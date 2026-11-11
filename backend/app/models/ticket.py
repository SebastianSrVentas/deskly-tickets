"""Esquemas Pydantic v2 del dominio de tickets."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Estado(StrEnum):
    ABIERTO = "abierto"
    EN_PROGRESO = "en_progreso"
    RESUELTO = "resuelto"
    CERRADO = "cerrado"


class Prioridad(StrEnum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


Titulo = Annotated[str, Field(min_length=3, max_length=120, examples=["Error al iniciar sesion"])]
Descripcion = Annotated[str, Field(min_length=1, max_length=4000)]
Autor = Annotated[str, Field(min_length=2, max_length=80)]
TextoComentario = Annotated[str, Field(min_length=1, max_length=2000)]


class ConfiguracionEntrada(BaseModel):
    """Base de las entradas: rechaza campos desconocidos y recorta espacios.

    Rechazar campos desconocidos es lo que impide que un PATCH cambie `estado`
    y se salte la maquina de estados: devuelve 422 sin codigo extra.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ComentarioCrear(ConfiguracionEntrada):
    autor: Autor
    texto: TextoComentario


class TicketCrear(ConfiguracionEntrada):
    titulo: Titulo
    descripcion: Descripcion
    prioridad: Prioridad = Prioridad.MEDIA
    asignado_a: str | None = Field(default=None, max_length=80)

    @field_validator("asignado_a")
    @classmethod
    def normalizar_asignado(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        limpio = valor.strip()
        return limpio or None


class TicketActualizar(ConfiguracionEntrada):
    """Campos descriptivos. El estado solo cambia por /transicion."""

    titulo: Titulo | None = None
    descripcion: Descripcion | None = None
    prioridad: Prioridad | None = None
    asignado_a: str | None = Field(default=None, max_length=80)

    @field_validator("asignado_a")
    @classmethod
    def normalizar_asignado(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        limpio = valor.strip()
        return limpio or None


class TransicionCrear(ConfiguracionEntrada):
    estado_destino: Estado
    motivo: Annotated[str, Field(max_length=300)] | None = None


class ComentarioSalida(BaseModel):
    id: str
    autor: str
    texto: str
    creado_en: datetime


class TicketSalida(BaseModel):
    id: str
    titulo: str
    descripcion: str
    prioridad: Prioridad
    estado: Estado
    asignado_a: str | None
    comentarios: list[ComentarioSalida] = Field(default_factory=list)
    creado_en: datetime
    actualizado_en: datetime


class PaginaTickets(BaseModel):
    items: list[TicketSalida]
    total: int
    pagina: int
    por_pagina: int
    paginas: int
