"""WebSocket de eventos de tickets.

Un unico listener de Redis Pub/Sub hace fan-out a todas las conexiones de esta
replica. Con varias replicas, cada una recibe el mismo evento por Pub/Sub y lo
entrega a sus propios clientes: no hay estado compartido en memoria.

El listener usa un cliente Redis dedicado sin ``socket_timeout`` porque
``pubsub.listen()`` es una lectura bloqueada de larga duracion; el cliente
global, con timeout de 2 s, cortaria la suscripcion.
"""

import asyncio
import json
from contextlib import suppress

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.cola.publicador import CANAL_EVENTOS
from app.config import get_settings
from app.observabilidad.logging import obtener_logger

router = APIRouter()
logger = obtener_logger(__name__)


class GestorConexiones:
    """Registro de WebSockets con suscripcion opcional a un ticket."""

    def __init__(self) -> None:
        self._conexiones: dict[WebSocket, str | None] = {}
        self._lock = asyncio.Lock()

    async def conectar(self, websocket: WebSocket, ticket_id: str | None = None) -> None:
        await websocket.accept()
        async with self._lock:
            self._conexiones[websocket] = ticket_id

    async def desconectar(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._conexiones.pop(websocket, None)

    async def difundir(self, mensaje: dict) -> None:
        ticket_id = mensaje.get("ticket_id")
        async with self._lock:
            destinos = [
                websocket
                for websocket, suscripcion in self._conexiones.items()
                if suscripcion is None or suscripcion == ticket_id
            ]

        if not destinos:
            return

        resultados = await asyncio.gather(
            *(websocket.send_json(mensaje) for websocket in destinos),
            return_exceptions=True,
        )
        for websocket, resultado in zip(destinos, resultados, strict=True):
            if isinstance(resultado, Exception):
                await self.desconectar(websocket)


gestor = GestorConexiones()


def _mensaje(cliente: str) -> dict | None:
    try:
        evento = json.loads(cliente)
    except json.JSONDecodeError:
        logger.warning("ws_evento_json_invalido")
        return None

    datos = evento.get("datos")
    if isinstance(datos, str):
        try:
            datos = json.loads(datos)
        except json.JSONDecodeError:
            datos = None

    return {
        "tipo": evento.get("tipo"),
        "event_id": evento.get("event_id"),
        "ticket_id": evento.get("ticket_id"),
        "ocurrido_en": evento.get("ocurrido_en"),
        "datos": datos,
    }


async def escuchar_eventos() -> None:
    """Se suscribe a Pub/Sub y reenvia cada evento a los clientes.

    Si Redis cae, reintenta cada 2 segundos sin tumbar el proceso: los
    WebSockets existentes siguen abiertos aunque no reciban eventos.
    """
    settings = get_settings()

    while True:
        cliente = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=0,
        )
        pubsub = cliente.pubsub()
        try:
            await pubsub.subscribe(CANAL_EVENTOS)
            logger.info("ws_suscrito", extra={"canal": CANAL_EVENTOS})
            async for mensaje in pubsub.listen():
                if mensaje.get("type") != "message":
                    continue
                evento = _mensaje(mensaje.get("data") or "")
                if evento is not None:
                    await gestor.difundir(evento)
        except asyncio.CancelledError:
            raise
        except (RedisError, OSError) as exc:
            logger.warning(
                "ws_redis_desconectado",
                extra={"motivo": f"{type(exc).__name__}: {exc}"},
            )
        finally:
            with suppress(Exception):
                await pubsub.aclose()
                await cliente.aclose()

        await asyncio.sleep(2)


@router.websocket("/ws/tickets")
async def tickets_ws(websocket: WebSocket, ticket_id: str | None = None) -> None:
    """Canal de eventos. ``?ticket_id=...`` limita la suscripcion a un ticket."""
    try:
        await gestor.conectar(websocket, ticket_id)
        await websocket.send_json({"tipo": "conectado", "ticket_id": ticket_id})
        while True:
            texto = await websocket.receive_text()
            if texto == "ping":
                await websocket.send_json({"tipo": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await gestor.desconectar(websocket)
