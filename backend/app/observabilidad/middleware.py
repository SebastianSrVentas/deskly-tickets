"""Middleware que genera el identificador de correlacion y registra cada request."""

import re
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.observabilidad.logging import obtener_logger

logger = obtener_logger(__name__)

_PATRON_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


def validar_request_id(valor: str | None) -> str:
    """Acepta el ID del cliente solo si es seguro para logs y trazas.

    Sin esta validacion, un cliente puede inyectar saltos de linea en el log
    o un identificador arbitrariamente largo.
    """
    if valor and _PATRON_REQUEST_ID.fullmatch(valor):
        return valor
    return uuid.uuid4().hex


class MiddlewareContexto(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = validar_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        inicio = time.perf_counter()

        try:
            respuesta = await call_next(request)
        except Exception:
            logger.exception(
                "peticion_fallida",
                extra={
                    "request_id": request_id,
                    "metodo": request.method,
                    "ruta": request.url.path,
                    "duracion_ms": round((time.perf_counter() - inicio) * 1000, 2),
                },
            )
            raise

        duracion_ms = round((time.perf_counter() - inicio) * 1000, 2)
        respuesta.headers["X-Request-ID"] = request_id
        logger.info(
            "peticion",
            extra={
                "request_id": request_id,
                "metodo": request.method,
                "ruta": request.url.path,
                "status": respuesta.status_code,
                "duracion_ms": duracion_ms,
            },
        )
        return respuesta
