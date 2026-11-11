"""Webhook de ingesta de tickets desde sistemas externos.

Contrato del brief:
- ``POST /api/webhooks/tickets``
- Firma HMAC-SHA256 en ``X-Signature`` sobre ``timestamp.client_id.body``.
- Firma invalida -> 401. Payload malformado -> 422.
- ``event_id`` repetido no crea otro ticket (200 con el original).
"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response, status
from pydantic import ValidationError

from app.cola.publicador import publicar_evento
from app.config import Settings, get_settings
from app.db import get_coleccion_tickets
from app.errores import (
    ClienteNoAutorizado,
    CuerpoDemasiadoGrande,
    EventoDuplicado,
    FirmaInvalida,
    LimiteExcedido,
    PayloadInvalido,
    TimestampExpirado,
)
from app.models.ticket import TicketCrear, TicketSalida
from app.models.webhook import WebhookTicketCrear
from app.observabilidad.metricas import DESFASE_WEBHOOK, TICKETS_CREADOS, WEBHOOK
from app.repositories.tickets import RepositorioTickets
from app.seguridad.hmac import desfase_segundos, timestamp_valido, verificar_firma
from app.seguridad.rate_limit import consumir

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def obtener_repositorio() -> RepositorioTickets:
    return RepositorioTickets(get_coleccion_tickets())


def obtener_settings() -> Settings:
    return get_settings()


Repositorio = Annotated[RepositorioTickets, Depends(obtener_repositorio)]
Config = Annotated[Settings, Depends(obtener_settings)]


async def _limitar(clave: str, capacidad: int, tasa: int, ambito: str) -> None:
    resultado = await consumir(clave, capacidad, tasa)
    if not resultado.permitido:
        raise LimiteExcedido(
            mensaje=f"Limite de solicitudes excedido para {ambito}",
            detalles={
                "ambito": ambito,
                "limite": resultado.limite,
                "reintentar_en_segundos": resultado.reintentar_en_segundos,
            },
        )


def _demasiado_grande(request: Request, maximo: int) -> bool:
    crudo = request.headers.get("content-length")
    if not crudo:
        return False
    try:
        return int(crudo) > maximo
    except ValueError:
        return False


@router.post(
    "/tickets",
    response_model=TicketSalida,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un ticket desde un sistema externo",
    description=(
        "Verifica la firma HMAC-SHA256 sobre `timestamp.client_id.body`. "
        "El mismo `event_id` devuelve 200 con el ticket original."
    ),
)
async def recibir_ticket(
    request: Request,
    response: Response,
    repositorio: Repositorio,
    config: Config,
    x_client_id: Annotated[str | None, Header(alias="X-Client-Id")] = None,
    x_timestamp: Annotated[str | None, Header(alias="X-Timestamp")] = None,
    x_signature: Annotated[str | None, Header(alias="X-Signature")] = None,
) -> TicketSalida:
    ip = request.client.host if request.client else "desconocida"
    await _limitar(
        f"rl:webhook:ip:{ip}",
        config.rate_limit_ip_rafaga,
        config.rate_limit_ip_por_segundo,
        "ip",
    )

    if not x_client_id or not x_timestamp or not x_signature:
        raise FirmaInvalida(mensaje="Faltan X-Client-Id, X-Timestamp o X-Signature")

    if not config.webhook_configurado:
        raise ClienteNoAutorizado(mensaje="El webhook no tiene secreto configurado")

    if _demasiado_grande(request, config.webhook_max_body_bytes):
        raise CuerpoDemasiadoGrande(detalles={"maximo_bytes": config.webhook_max_body_bytes})

    cuerpo = await request.body()
    if len(cuerpo) > config.webhook_max_body_bytes:
        raise CuerpoDemasiadoGrande(detalles={"maximo_bytes": config.webhook_max_body_bytes})

    if not timestamp_valido(x_timestamp, config.webhook_tolerancia_segundos):
        WEBHOOK.labels(cliente=x_client_id, resultado="timestamp_invalido").inc()
        raise TimestampExpirado(
            detalles={"tolerancia_segundos": config.webhook_tolerancia_segundos}
        )

    clientes = config.clientes_webhook
    if clientes:
        secretos = clientes.get(x_client_id)
        if not secretos:
            WEBHOOK.labels(cliente=x_client_id, resultado="cliente_no_autorizado").inc()
            raise ClienteNoAutorizado(detalles={"cliente_id": x_client_id})
    elif config.webhook_secret:
        secretos = [config.webhook_secret]
    else:
        raise ClienteNoAutorizado(mensaje="El webhook no tiene secreto configurado")

    if not any(
        verificar_firma(secreto, x_timestamp, x_client_id, cuerpo, x_signature)
        for secreto in secretos
    ):
        WEBHOOK.labels(cliente=x_client_id, resultado="firma_invalida").inc()
        raise FirmaInvalida(detalles={"cliente_id": x_client_id})

    await _limitar(
        f"rl:webhook:cliente:{x_client_id}",
        config.rate_limit_cliente_rafaga,
        config.rate_limit_cliente_por_segundo,
        "cliente",
    )

    desfase = desfase_segundos(x_timestamp)
    if desfase is not None:
        DESFASE_WEBHOOK.observe(desfase)

    try:
        crudo = json.loads(cuerpo)
    except json.JSONDecodeError as exc:
        WEBHOOK.labels(cliente=x_client_id, resultado="payload_invalido").inc()
        raise PayloadInvalido(mensaje="El cuerpo no es JSON valido") from exc

    if not isinstance(crudo, dict):
        WEBHOOK.labels(cliente=x_client_id, resultado="payload_invalido").inc()
        raise PayloadInvalido(mensaje="El cuerpo debe ser un objeto JSON")

    try:
        datos = WebhookTicketCrear.model_validate(crudo)
    except ValidationError as exc:
        WEBHOOK.labels(cliente=x_client_id, resultado="payload_invalido").inc()
        errores = [
            {
                "campo": ".".join(str(parte) for parte in error["loc"]),
                "tipo": error["type"],
                "mensaje": error["msg"],
            }
            for error in exc.errors()
        ]
        raise PayloadInvalido(detalles={"errores": errores}) from exc

    ticket_base = TicketCrear(
        titulo=datos.titulo,
        descripcion=datos.descripcion,
        prioridad=datos.prioridad,
        asignado_a=datos.asignado_a,
    )

    try:
        ticket = await repositorio.crear(
            ticket_base,
            origen={"tipo": "webhook", "cliente_id": x_client_id},
            event_id=datos.event_id,
        )
        creado = True
    except EventoDuplicado as duplicado:
        ticket = duplicado.ticket
        creado = False

    if creado:
        TICKETS_CREADOS.labels(origen="webhook").inc()
        await publicar_evento("ticket.creado", ticket, cliente_id=x_client_id)

    WEBHOOK.labels(cliente=x_client_id, resultado="creado" if creado else "duplicado").inc()

    if not creado:
        response.status_code = status.HTTP_200_OK
    return ticket
