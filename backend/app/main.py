"""Punto de entrada de la API Deskly."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from redis.exceptions import RedisError

from app.api.tickets import router as tickets_router
from app.api.webhooks import router as webhooks_router
from app.api.ws import escuchar_eventos
from app.api.ws import router as ws_router
from app.config import get_settings
from app.db import basedatos
from app.errores import registrar_handlers
from app.observabilidad.logging import configurar_logging, obtener_logger
from app.observabilidad.middleware import MiddlewareContexto
from app.redis import conexion_redis

settings = get_settings()
logger = obtener_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Abre las conexiones al arrancar y las cierra al apagar.

    MongoDB es obligatorio: sin el no hay servicio. Redis es opcional en el
    arranque: si no esta, la API REST sigue funcionando en modo degradado y
    solo se pierden eventos en vivo y rate limiting.
    """
    configurar_logging(settings.log_level)
    await basedatos.conectar(settings)

    try:
        await conexion_redis.conectar(settings)
    except (RedisError, OSError):
        logger.error(
            "redis_no_disponible_al_arrancar",
            extra={"motivo": "la API arranca en modo degradado"},
        )

    logger.info("aplicacion_iniciada", extra={"entorno": settings.entorno})
    tarea_eventos = asyncio.create_task(escuchar_eventos())
    yield

    tarea_eventos.cancel()
    with suppress(asyncio.CancelledError):
        await tarea_eventos

    await conexion_redis.cerrar()
    await basedatos.cerrar()
    logger.info("aplicacion_detenida")


app = FastAPI(
    title=settings.app_name,
    description="Prototipo de sistema de tickets de soporte para Deskly",
    version=settings.version,
    lifespan=lifespan,
)

# El ultimo middleware agregado es el mas externo: el contexto debe envolver
# a CORS para que el header X-Request-ID aparezca incluso en respuestas CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MiddlewareContexto)

registrar_handlers(app)

Instrumentator().instrument(app).expose(
    app,
    endpoint="/metrics",
    include_in_schema=False,
)


@app.get("/api/health", tags=["salud"])
async def health() -> dict[str, str]:
    """Liveness: responde si el proceso esta vivo."""
    return {"estado": "ok", "version": settings.version}


@app.get("/api/health/ready", tags=["salud"])
async def ready(response: Response) -> dict[str, str]:
    """Readiness: MongoDB obligatorio, Redis reportado como dependencia opcional."""
    mongo_ok = True
    try:
        if basedatos.db is None:
            raise RuntimeError("MongoDB no esta conectado")
        await basedatos.db.command("ping")
    except Exception as exc:
        mongo_ok = False
        logger.warning(
            "mongo_no_disponible",
            extra={"motivo": f"{type(exc).__name__}: {exc}"},
        )

    redis_ok = await conexion_redis.esta_disponible()

    if not mongo_ok:
        response.status_code = 503
        estado = "no_disponible"
    elif not redis_ok:
        estado = "degradado"
    else:
        estado = "ok"

    return {
        "estado": estado,
        "mongo": "ok" if mongo_ok else "caido",
        "redis": "ok" if redis_ok else "caido",
    }


# Routers
app.include_router(tickets_router)
app.include_router(webhooks_router)
app.include_router(ws_router)
