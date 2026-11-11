"""Endpoints REST de tickets."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.cola.publicador import publicar_evento
from app.db import get_coleccion_tickets
from app.models.ticket import (
    ComentarioCrear,
    Estado,
    PaginaTickets,
    Prioridad,
    TicketActualizar,
    TicketCrear,
    TicketSalida,
    TransicionCrear,
)
from app.observabilidad.metricas import TICKETS_CREADOS, TRANSICIONES
from app.repositories.tickets import RepositorioTickets

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def obtener_repositorio() -> RepositorioTickets:
    return RepositorioTickets(get_coleccion_tickets())


Repositorio = Annotated[RepositorioTickets, Depends(obtener_repositorio)]


@router.post(
    "",
    response_model=TicketSalida,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un ticket",
    description="Crea un ticket en estado 'abierto' y publica ticket.creado en Redis.",
)
async def crear_ticket(datos: TicketCrear, repositorio: Repositorio) -> TicketSalida:
    ticket = await repositorio.crear(datos)
    TICKETS_CREADOS.labels(origen="api").inc()
    await publicar_evento("ticket.creado", ticket)
    return ticket


@router.get(
    "",
    response_model=PaginaTickets,
    summary="Listar tickets",
    description="Listado paginado, ordenado del mas reciente al mas antiguo.",
)
async def listar_tickets(
    repositorio: Repositorio,
    estado: Annotated[Estado | None, Query(description="Filtra por estado")] = None,
    prioridad: Annotated[Prioridad | None, Query(description="Filtra por prioridad")] = None,
    q: Annotated[
        str | None,
        Query(max_length=120, description="Busca en titulo y descripcion"),
    ] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 10,
) -> PaginaTickets:
    return await repositorio.listar(estado, prioridad, q, pagina, por_pagina)


@router.get(
    "/{ticket_id}",
    response_model=TicketSalida,
    summary="Detalle de un ticket",
)
async def obtener_ticket(ticket_id: str, repositorio: Repositorio) -> TicketSalida:
    return await repositorio.obtener(ticket_id)


@router.patch(
    "/{ticket_id}",
    response_model=TicketSalida,
    summary="Actualizar campos descriptivos",
    description=(
        "Solo titulo, descripcion, prioridad y asignado_a. "
        "El estado se cambia exclusivamente por /transicion; enviarlo aqui devuelve 422."
    ),
)
async def actualizar_ticket(
    ticket_id: str,
    datos: TicketActualizar,
    repositorio: Repositorio,
) -> TicketSalida:
    ticket = await repositorio.actualizar(ticket_id, datos)
    await publicar_evento("ticket.actualizado", ticket)
    return ticket


@router.post(
    "/{ticket_id}/transicion",
    response_model=TicketSalida,
    summary="Cambiar el estado",
    description=(
        "Transiciones validas: abierto -> en_progreso -> resuelto -> cerrado. "
        "Desde resuelto se puede reabrir a abierto. Una transicion invalida devuelve 409."
    ),
)
async def transicionar_ticket(
    ticket_id: str,
    datos: TransicionCrear,
    repositorio: Repositorio,
) -> TicketSalida:
    ticket = await repositorio.transicionar(ticket_id, datos)
    TRANSICIONES.labels(destino=ticket.estado.value).inc()
    await publicar_evento("ticket.actualizado", ticket)
    return ticket


@router.post(
    "/{ticket_id}/comentarios",
    response_model=TicketSalida,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar un comentario",
)
async def comentar_ticket(
    ticket_id: str,
    datos: ComentarioCrear,
    repositorio: Repositorio,
) -> TicketSalida:
    ticket = await repositorio.comentar(ticket_id, datos)
    await publicar_evento("ticket.comentado", ticket)
    return ticket
