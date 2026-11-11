"""Consumidor de Redis Streams con ack, reintentos y dead letter queue.

Garantias:
- at-least-once: un mensaje se confirma solo despues de procesarlo.
- reintento: si el manejador falla, el mensaje queda pendiente y se reclama
  cuando el consumidor lleva demasiado tiempo sin confirmarlo.
- dead letter: tras N intentos se mueve a otro stream y se alerta.
"""

import asyncio
import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from redis.asyncio import Redis
from redis.exceptions import RedisError, ResponseError

from app.observabilidad.logging import obtener_logger
from app.observabilidad.metricas import COLA_PENDIENTES

logger = obtener_logger(__name__)

Manejador = Callable[[dict[str, str]], Awaitable[None]]


@dataclass
class ConfiguracionConsumidor:
    stream: str = "deskly:cola"
    grupo: str = "deskly-workers"
    nombre: str = field(default_factory=lambda: f"worker-{socket.gethostname()}")
    lote: int = 10
    bloqueo_ms: int = 5_000
    max_intentos: int = 3
    intervalo_reclamo_s: int = 60
    idle_reclamo_ms: int = 60_000
    stream_muertos: str = "deskly:cola:muertos"


class Consumidor:
    def __init__(
        self,
        cliente: Redis,
        manejador: Manejador,
        config: ConfiguracionConsumidor | None = None,
    ) -> None:
        self.cliente = cliente
        self.manejador = manejador
        self.config = config or ConfiguracionConsumidor()

    async def asegurar_grupo(self) -> None:
        """Crea el consumer group si no existe.

        Con varias replicas del worker, la segunda recibe BUSYGROUP y debe
        continuar: el grupo ya existe y es compartido.
        """
        try:
            await self.cliente.xgroup_create(
                self.config.stream,
                self.config.grupo,
                id="0",
                mkstream=True,
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def ejecutar(self, detener: asyncio.Event) -> None:
        await self.asegurar_grupo()
        ultimo_reclamo = 0.0

        while not detener.is_set():
            try:
                respuesta = await self.cliente.xreadgroup(
                    self.config.grupo,
                    self.config.nombre,
                    {self.config.stream: ">"},
                    count=self.config.lote,
                    block=self.config.bloqueo_ms,
                )
            except RedisError:
                logger.exception("lectura_cola_fallida")
                await asyncio.sleep(1)
                continue

            for _, mensajes in respuesta or []:
                for msg_id, campos in mensajes:
                    await self._procesar(msg_id, campos)

            await self._actualizar_metricas()

            ahora = asyncio.get_running_loop().time()
            if ahora - ultimo_reclamo >= self.config.intervalo_reclamo_s:
                await self.recuperar_pendientes()
                ultimo_reclamo = ahora

    async def recuperar_pendientes(self) -> None:
        """Reclama mensajes de consumidores que murieron sin hacer ack."""
        try:
            resultado = await self.cliente.xautoclaim(
                self.config.stream,
                self.config.grupo,
                self.config.nombre,
                min_idle_time=self.config.idle_reclamo_ms,
                start_id="0-0",
                count=self.config.lote,
            )
        except RedisError:
            logger.exception("reclamo_pendientes_fallido")
            return

        mensajes = resultado[1] if len(resultado) > 1 else []
        for msg_id, campos in mensajes:
            if not campos:
                continue
            logger.warning("mensaje_reclamado", extra={"event_id": campos.get("event_id")})
            await self._procesar(msg_id, campos)

    async def _procesar(self, msg_id: str, campos: dict[str, str]) -> None:
        try:
            await self.manejador(campos)
        except Exception:
            intentos = await self._contar_intento(msg_id)
            logger.exception(
                "mensaje_fallido",
                extra={
                    "event_id": campos.get("event_id"),
                    "motivo": f"intento {intentos} de {self.config.max_intentos}",
                },
            )
            if intentos >= self.config.max_intentos:
                await self._mover_a_muertos(msg_id, campos, intentos)
                await self.cliente.xack(self.config.stream, self.config.grupo, msg_id)
            return

        await self.cliente.xack(self.config.stream, self.config.grupo, msg_id)

    async def _contar_intento(self, msg_id: str) -> int:
        clave = f"deskly:cola:intentos:{msg_id}"
        intentos = await self.cliente.hincrby(clave, "total", 1)
        await self.cliente.expire(clave, 3_600)
        return int(intentos)

    async def _mover_a_muertos(
        self,
        msg_id: str,
        campos: dict[str, str],
        intentos: int,
    ) -> None:
        await self.cliente.xadd(
            self.config.stream_muertos,
            {
                "msg_id_original": msg_id,
                "intentos": str(intentos),
                **campos,
            },
            maxlen=1_000,
            approximate=True,
        )
        logger.error(
            "mensaje_a_muertos",
            extra={"event_id": campos.get("event_id"), "motivo": "maximo de intentos"},
        )

    async def _actualizar_metricas(self) -> None:
        try:
            COLA_PENDIENTES.set(await self.cliente.xlen(self.config.stream))
        except RedisError:
            logger.warning("metrica_cola_no_actualizada")
