"""Payload que acepta el webhook de ingesta.

Hereda de ``TicketCrear`` para reutilizar las mismas validaciones y el
``extra="forbid"``: un campo desconocido en el webhook tambien da 422.
"""

from pydantic import Field

from app.models.ticket import TicketCrear


class WebhookTicketCrear(TicketCrear):
    """Ticket externo con ``event_id`` para idempotencia.

    El ``event_id`` es opcional para no romper clientes que aun no lo envian,
    pero sin el no hay garantia de que un reintento no cree otro ticket.
    """

    event_id: str | None = Field(default=None, min_length=8, max_length=128)
