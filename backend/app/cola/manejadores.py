"""Manejadores de eventos de la cola.

Este modulo es el punto de extension: cada tipo de evento puede tener su
propia funcion. El manejador por defecto deja rastro en la coleccion de
auditoria; los envios externos se agregan aqui cuando existan.
"""

from datetime import UTC, datetime

from pymongo.errors import DuplicateKeyError

from app.db import basedatos
from app.observabilidad.logging import obtener_logger

logger = obtener_logger(__name__)


async def manejar_evento(campos: dict[str, str]) -> None:
    """Registra el evento en auditoria de forma idempotente.

    El indice unico sobre event_id hace que un reintento no duplique el
    registro: DuplicateKeyError se trata como evento ya procesado.
    """
    event_id = campos.get("event_id")
    if not event_id:
        raise ValueError("El evento no trae event_id")

    coleccion = basedatos.coleccion("auditoria")
    try:
        await coleccion.insert_one(
            {
                "event_id": event_id,
                "tipo": campos.get("tipo"),
                "ticket_id": campos.get("ticket_id"),
                "cliente_id": campos.get("cliente_id"),
                "ocurrido_en": campos.get("ocurrido_en"),
                "procesado_en": datetime.now(UTC),
            }
        )
    except DuplicateKeyError:
        logger.info("evento_ya_auditado", extra={"event_id": event_id})
