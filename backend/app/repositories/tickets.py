"""Acceso a la coleccion de tickets en MongoDB."""

import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from bson.errors import InvalidId
from bson.objectid import ObjectId
from pymongo import ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError

from app.domain.state_machine import validar_transicion
from app.errores import EventoDuplicado, TicketNoEncontrado, TransicionInvalida
from app.models.ticket import (
    ComentarioCrear,
    ComentarioSalida,
    Estado,
    PaginaTickets,
    Prioridad,
    TicketActualizar,
    TicketCrear,
    TicketSalida,
    TransicionCrear,
)


def object_id(ticket_id: str) -> ObjectId:
    try:
        return ObjectId(ticket_id)
    except (InvalidId, TypeError) as exc:
        raise TicketNoEncontrado() from exc


class RepositorioTickets:
    def __init__(self, coleccion: AsyncCollection) -> None:
        self.coleccion = coleccion

    async def crear(
        self,
        datos: TicketCrear,
        origen: dict[str, Any] | None = None,
        *,
        event_id: str | None = None,
    ) -> TicketSalida:
        ahora = datetime.now(UTC)
        documento: dict[str, Any] = {
            "titulo": datos.titulo,
            "descripcion": datos.descripcion,
            "prioridad": datos.prioridad.value,
            "estado": Estado.ABIERTO.value,
            "asignado_a": datos.asignado_a,
            "comentarios": [],
            "historial": [
                {
                    "anterior": None,
                    "nuevo": Estado.ABIERTO.value,
                    "motivo": "creacion",
                    "en": ahora,
                }
            ],
            "origen": origen or {"tipo": "api"},
            "creado_en": ahora,
            "actualizado_en": ahora,
        }

        # El indice unique sparse sobre event_id es la garantia de idempotencia:
        # dos requests concurrentes con el mismo evento solo insertan una.
        if event_id:
            documento["event_id"] = event_id

        try:
            resultado = await self.coleccion.insert_one(documento)
        except DuplicateKeyError as exc:
            if event_id:
                existente = await self.obtener_por_event_id(event_id)
                raise EventoDuplicado(existente) from exc
            raise

        documento["_id"] = resultado.inserted_id
        return self._a_salida(documento)

    async def obtener_por_event_id(self, event_id: str) -> TicketSalida:
        documento = await self.coleccion.find_one({"event_id": event_id})
        if documento is None:
            raise TicketNoEncontrado()
        return self._a_salida(documento)

    async def listar(
        self,
        estado: Estado | None,
        prioridad: Prioridad | None,
        q: str | None,
        pagina: int,
        por_pagina: int,
    ) -> PaginaTickets:
        filtro: dict[str, Any] = {}

        if estado is not None:
            filtro["estado"] = estado.value
        if prioridad is not None:
            filtro["prioridad"] = prioridad.value
        if q:
            patron = re.escape(q)
            filtro["$or"] = [
                {"titulo": {"$regex": patron, "$options": "i"}},
                {"descripcion": {"$regex": patron, "$options": "i"}},
            ]

        total = await self.coleccion.count_documents(filtro)
        cursor = (
            self.coleccion.find(filtro)
            .sort("creado_en", -1)
            .skip((pagina - 1) * por_pagina)
            .limit(por_pagina)
        )
        documentos = await cursor.to_list(length=por_pagina)

        paginas = max(1, (total + por_pagina - 1) // por_pagina)
        return PaginaTickets(
            items=[self._a_salida(documento) for documento in documentos],
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            paginas=paginas,
        )

    async def obtener(self, ticket_id: str) -> TicketSalida:
        documento = await self.coleccion.find_one({"_id": object_id(ticket_id)})
        if documento is None:
            raise TicketNoEncontrado()
        return self._a_salida(documento)

    async def actualizar(self, ticket_id: str, datos: TicketActualizar) -> TicketSalida:
        cambios = datos.model_dump(mode="json", exclude_unset=True)
        if not cambios:
            return await self.obtener(ticket_id)

        cambios["actualizado_en"] = datetime.now(UTC)
        documento = await self.coleccion.find_one_and_update(
            {"_id": object_id(ticket_id)},
            {"$set": cambios},
            return_document=ReturnDocument.AFTER,
        )
        if documento is None:
            raise TicketNoEncontrado()
        return self._a_salida(documento)

    async def transicionar(self, ticket_id: str, datos: TransicionCrear) -> TicketSalida:
        oid = object_id(ticket_id)
        actual = await self.coleccion.find_one({"_id": oid}, {"estado": 1})
        if actual is None:
            raise TicketNoEncontrado()

        estado_actual = Estado(actual["estado"])
        validar_transicion(estado_actual, datos.estado_destino)

        ahora = datetime.now(UTC)
        documento = await self.coleccion.find_one_and_update(
            # El filtro por estado hace la transicion atomica: si otra solicitud
            # cambio el estado entre la lectura y la escritura, no matchea.
            {"_id": oid, "estado": estado_actual.value},
            {
                "$set": {
                    "estado": datos.estado_destino.value,
                    "actualizado_en": ahora,
                },
                "$push": {
                    "historial": {
                        "anterior": estado_actual.value,
                        "nuevo": datos.estado_destino.value,
                        "motivo": datos.motivo,
                        "en": ahora,
                    }
                },
            },
            return_document=ReturnDocument.AFTER,
        )

        if documento is None:
            raise TransicionInvalida(
                mensaje="El ticket cambio de estado mientras se procesaba la solicitud",
                detalles={
                    "estado_actual": estado_actual.value,
                    "estado_solicitado": datos.estado_destino.value,
                },
            )

        return self._a_salida(documento)

    async def comentar(self, ticket_id: str, datos: ComentarioCrear) -> TicketSalida:
        ahora = datetime.now(UTC)
        comentario = {
            "id": uuid4().hex,
            "autor": datos.autor,
            "texto": datos.texto,
            "creado_en": ahora,
        }
        documento = await self.coleccion.find_one_and_update(
            {"_id": object_id(ticket_id)},
            {
                "$push": {"comentarios": comentario},
                "$set": {"actualizado_en": ahora},
            },
            return_document=ReturnDocument.AFTER,
        )
        if documento is None:
            raise TicketNoEncontrado()
        return self._a_salida(documento)

    def _a_salida(self, documento: dict[str, Any]) -> TicketSalida:
        return TicketSalida(
            id=str(documento["_id"]),
            titulo=documento["titulo"],
            descripcion=documento["descripcion"],
            prioridad=Prioridad(documento["prioridad"]),
            estado=Estado(documento["estado"]),
            asignado_a=documento.get("asignado_a"),
            comentarios=[
                ComentarioSalida(
                    id=comentario["id"],
                    autor=comentario["autor"],
                    texto=comentario["texto"],
                    creado_en=comentario["creado_en"],
                )
                for comentario in documento.get("comentarios", [])
            ],
            creado_en=documento["creado_en"],
            actualizado_en=documento["actualizado_en"],
        )
