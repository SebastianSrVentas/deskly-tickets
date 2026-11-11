"""Conexion asincrona a Redis: eventos, colas y rate limiting."""

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import Settings


class ConexionRedis:
    """Cliente Redis compartido por la aplicacion.

    Redis no es fuente de verdad: si cae, la API REST sigue sirviendo y los
    WebSockets quedan sin eventos nuevos hasta que vuelva.
    """

    def __init__(self) -> None:
        self.cliente: Redis | None = None

    async def conectar(
        self,
        settings: Settings,
        socket_timeout: float | None = 2,
    ) -> None:
        self.cliente = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=socket_timeout,
            socket_connect_timeout=2,
            health_check_interval=30,
        )
        await self.cliente.ping()

    async def cerrar(self) -> None:
        if self.cliente is not None:
            await self.cliente.aclose()
        self.cliente = None

    async def esta_disponible(self) -> bool:
        if self.cliente is None:
            return False
        try:
            return bool(await self.cliente.ping())
        except RedisError:
            return False

    def requerido(self) -> Redis:
        if self.cliente is None:
            raise RuntimeError("Redis no esta conectado")
        return self.cliente


conexion_redis = ConexionRedis()
