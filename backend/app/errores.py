"""Errores de dominio y traduccion uniforme a respuestas HTTP."""

from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.observabilidad.logging import obtener_logger

if TYPE_CHECKING:
    from app.models.ticket import TicketSalida

logger = obtener_logger(__name__)


class ErrorDominio(Exception):
    """Error esperado del negocio.

    Cada subclase define su codigo estable y su status HTTP. El cliente recibe
    un JSON uniforme y nunca un stack trace.
    """

    codigo = "error"
    status = 400
    mensaje = "Error de solicitud"

    def __init__(
        self,
        mensaje: str | None = None,
        detalles: dict[str, Any] | None = None,
    ) -> None:
        self.mensaje = mensaje or self.mensaje
        self.detalles = detalles or {}
        super().__init__(self.mensaje)


class TicketNoEncontrado(ErrorDominio):
    codigo = "ticket_no_encontrado"
    status = 404
    mensaje = "El ticket no existe"


class TransicionInvalida(ErrorDominio):
    codigo = "transicion_invalida"
    status = 409
    mensaje = "La transicion de estado no esta permitida"


class FirmaInvalida(ErrorDominio):
    codigo = "firma_invalida"
    status = 401
    mensaje = "Firma invalida"


class LimiteExcedido(ErrorDominio):
    codigo = "limite_excedido"
    status = 429
    mensaje = "Se excedio el limite de solicitudes"


class PayloadInvalido(ErrorDominio):
    codigo = "payload_invalido"
    status = 422
    mensaje = "El payload no es valido"


class TimestampExpirado(ErrorDominio):
    codigo = "timestamp_expirado"
    status = 401
    mensaje = "El timestamp de la firma esta fuera de la ventana permitida"


class ClienteNoAutorizado(ErrorDominio):
    codigo = "cliente_no_autorizado"
    status = 401
    mensaje = "El cliente no esta autorizado"


class CuerpoDemasiadoGrande(ErrorDominio):
    codigo = "cuerpo_demasiado_grande"
    status = 413
    mensaje = "El cuerpo supera el limite permitido"


class EventoDuplicado(Exception):
    """El ``event_id`` ya fue procesado.

    No es un ``ErrorDominio`` porque el webhook responde 200 con el ticket
    original: para el cliente es exito idempotente, no un error.
    """

    def __init__(self, ticket: TicketSalida) -> None:
        self.ticket = ticket
        super().__init__("Evento ya procesado")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "desconocido")


def _respuesta_error(
    request: Request,
    status: int,
    codigo: str,
    mensaje: str,
    detalles: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    cuerpo = {
        "codigo": codigo,
        "mensaje": mensaje,
        "detalles": detalles or {},
        "request_id": _request_id(request),
    }
    return JSONResponse(status_code=status, content=jsonable_encoder(cuerpo), headers=headers)


def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(ErrorDominio)
    async def manejar_error_dominio(request: Request, exc: ErrorDominio) -> JSONResponse:
        headers = None
        if isinstance(exc, LimiteExcedido):
            reintentar = exc.detalles.get("reintentar_en_segundos", 1)
            headers = {"Retry-After": str(max(1, int(reintentar)))}
        return _respuesta_error(
            request,
            status=exc.status,
            codigo=exc.codigo,
            mensaje=exc.mensaje,
            detalles=exc.detalles,
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def manejar_validacion(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errores = [
            {
                "campo": ".".join(str(parte) for parte in error["loc"] if parte != "body"),
                "tipo": error["type"],
                "mensaje": error["msg"],
            }
            for error in exc.errors()
        ]
        return _respuesta_error(
            request,
            status=422,
            codigo="validacion_fallida",
            mensaje="Uno o mas campos no son validos",
            detalles={"errores": errores},
        )

    @app.exception_handler(Exception)
    async def manejar_error_no_controlado(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "error_no_controlado",
            extra={
                "request_id": _request_id(request),
                "metodo": request.method,
                "ruta": request.url.path,
            },
        )
        return _respuesta_error(
            request,
            status=500,
            codigo="error_interno",
            mensaje="Ocurrio un error inesperado",
        )
