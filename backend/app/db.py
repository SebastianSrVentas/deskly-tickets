"""Conexion a MongoDB e indices de la aplicacion."""

from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.config import Settings
from app.observabilidad.logging import obtener_logger

logger = obtener_logger(__name__)


class BaseDeDatos:
    """Envoltorio del cliente asincrono de MongoDB.

    Se inicializa en el lifespan de FastAPI y se cierra al apagar.
    """

    def __init__(self) -> None:
        self.cliente: AsyncMongoClient | None = None
        self.db: AsyncDatabase | None = None

    async def conectar(self, settings: Settings) -> None:
        self.cliente = AsyncMongoClient(
            settings.mongo_url,
            tz_aware=True,
            serverSelectionTimeoutMS=5_000,
        )
        self.db = self.cliente[settings.mongo_db]
        await self.crear_indices()
        logger.info("mongo_conectado", extra={"motivo": settings.mongo_db})

    async def crear_indices(self) -> None:
        """Crea los indices de forma idempotente.

        - (estado, creado_en): cubre el listado filtrado por estado y ordenado
          por fecha de creacion, que es el caso de uso principal del dashboard.
        - (prioridad, creado_en): mismo patron para el filtro por prioridad.
        - event_id unico y sparse: idempotencia del webhook. Sparse permite que
          los tickets creados por la API no necesiten event_id.
        """
        if self.db is None:
            raise RuntimeError("La base de datos no esta conectada")

        tickets = self.db["tickets"]
        await tickets.create_index(
            [("estado", 1), ("creado_en", -1)],
            name="estado_creado_en",
        )
        await tickets.create_index(
            [("prioridad", 1), ("creado_en", -1)],
            name="prioridad_creado_en",
        )
        await tickets.create_index(
            "event_id",
            unique=True,
            sparse=True,
            name="event_id_unico",
        )

        # Auditoria escrita por el worker. event_id unico: un reintento del
        # consumidor no duplica el registro.
        auditoria = self.db["auditoria"]
        await auditoria.create_index(
            "event_id",
            unique=True,
            sparse=True,
            name="auditoria_event_id_unico",
        )
        await auditoria.create_index("ticket_id", name="auditoria_ticket_id")
        await auditoria.create_index("procesado_en", name="auditoria_procesado_en")

    async def cerrar(self) -> None:
        if self.cliente is not None:
            await self.cliente.close()
        self.cliente = None
        self.db = None
        logger.info("mongo_cerrado")

    def coleccion(self, nombre: str) -> AsyncCollection:
        if self.db is None:
            raise RuntimeError("La base de datos no esta conectada")
        return self.db[nombre]


basedatos = BaseDeDatos()


def get_coleccion_tickets() -> AsyncCollection:
    """Dependencia de FastAPI para inyectar la coleccion de tickets."""
    return basedatos.coleccion("tickets")
