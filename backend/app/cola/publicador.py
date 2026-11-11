"""Publicacion de eventos a Redis.

Dos canales:
- PUBLISH: fan-out inmediato a los WebSockets de todas las replicas.
- XADD: cola persistente para el worker, con ack y reintentos.

Si Redis falla, la respuesta HTTP no se rompe: el ticket ya esta en MongoDB.
"""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from redis.exceptions import RedisError

from app.models.ticket import TicketSalida
from app.observabilidad.logging import obtener_logger
from app.observabilidad.metricas import EVENTOS_FALLIDOS
from app.redis import conexion_redis

logger = obtener_logger(__name__)

CANAL_EVENTOS = "deskly:eventos"
STREAM_COLA = "deskly:cola"


async def publicar_evento(
    tipo: str,
    ticket: TicketSalida,
    *,
    cliente_id: str | None = None,
) -> None:
    cliente = conexion_redis.cliente
    if cliente is None:
        EVENTOS_FALLIDOS.labels(canal="sin_conexion").inc()
        return

    campos: dict[str, Any] = {
        "tipo": tipo,
        "event_id": uuid4().hex,
        "ticket_id": ticket.id,
        "ocurrido_en": datetime.now(UTC).isoformat(),
        "datos": json.dumps(ticket.model_dump(mode="json"), ensure_ascii=False),
    }
    if cliente_id:
        campos["cliente_id"] = cliente_id

    try:
        async with cliente.pipeline(transaction=False) as pipe:
            pipe.publish(CANAL_EVENTOS, json.dumps(campos, ensure_ascii=False))
            pipe.xadd(STREAM_COLA, campos, maxlen=10_000, approximate=True)
            await pipe.execute()
    except (RedisError, RuntimeError):
        EVENTOS_FALLIDOS.labels(canal="redis").inc()
        logger.warning(
            "evento_no_publicado",
            extra={"event_id": campos["event_id"], "motivo": "redis no disponible"},
        )
