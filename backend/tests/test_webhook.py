"""Tests del webhook: firma valida, firma invalida, replay, payload y idempotencia.

No usa Mongo ni Redis: el repositorio se reemplaza por un fake y la publicacion
se monkeypatchea. Asi el test corre en CI con un simple `pytest`.
"""

import hashlib
import hmac
import json
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from app.api.webhooks import obtener_repositorio, obtener_settings
from app.config import Settings
from app.errores import EventoDuplicado
from app.main import app
from app.models.ticket import Estado, TicketSalida

SECRETO = "secreto_test"
CLIENTE = "crm_test"


def firmar(
    cuerpo: str,
    timestamp: str,
    cliente: str = CLIENTE,
    secreto: str = SECRETO,
) -> str:
    material = f"{timestamp}.{cliente}.".encode() + cuerpo.encode("utf-8")
    return hmac.new(secreto.encode("utf-8"), material, hashlib.sha256).hexdigest()


class RepositorioFalso:
    """Imita la parte del repositorio que usa el webhook."""

    def __init__(self) -> None:
        self.tickets: dict[str, TicketSalida] = {}
        self.eventos: dict[str, TicketSalida] = {}

    async def crear(
        self,
        datos: Any,
        origen: dict[str, Any] | None = None,
        *,
        event_id: str | None = None,
    ) -> TicketSalida:
        if event_id and event_id in self.eventos:
            raise EventoDuplicado(self.eventos[event_id])

        ahora = datetime.now(UTC)
        ticket = TicketSalida(
            id=f"{len(self.tickets) + 1:024d}",
            titulo=datos.titulo,
            descripcion=datos.descripcion,
            prioridad=datos.prioridad,
            estado=Estado.ABIERTO,
            asignado_a=datos.asignado_a,
            comentarios=[],
            creado_en=ahora,
            actualizado_en=ahora,
        )
        self.tickets[ticket.id] = ticket
        if event_id:
            self.eventos[event_id] = ticket
        return ticket


@pytest.fixture
def repo() -> RepositorioFalso:
    return RepositorioFalso()


@pytest.fixture
def eventos(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    capturados: list[str] = []

    async def falso(tipo: str, ticket: TicketSalida, *, cliente_id: str | None = None) -> None:
        capturados.append(tipo)

    monkeypatch.setattr("app.api.webhooks.publicar_evento", falso)
    return capturados


@pytest.fixture
async def cliente(
    repo: RepositorioFalso,
    eventos: list[str],
) -> Iterator[httpx.AsyncClient]:
    app.dependency_overrides[obtener_repositorio] = lambda: repo
    app.dependency_overrides[obtener_settings] = lambda: Settings(
        webhook_secret=SECRETO,
        webhook_clientes=json.dumps({CLIENTE: SECRETO}),
        webhook_tolerancia_segundos=300,
    )
    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://test") as async_cliente:
        yield async_cliente
    app.dependency_overrides.clear()


def payload(event_id: str | None = "evt_prueba_0001") -> str:
    datos: dict[str, str] = {
        "titulo": "Ticket desde webhook",
        "descripcion": "Creado por el sistema externo",
        "prioridad": "alta",
        "asignado_a": "Ana Torres",
    }
    if event_id:
        datos["event_id"] = event_id
    return json.dumps(datos, separators=(",", ":"), ensure_ascii=False)


def cabeceras(
    cuerpo: str,
    *,
    timestamp: str | None = None,
    firma: str | None = None,
    cliente: str = CLIENTE,
) -> dict[str, str]:
    ts = timestamp or str(int(time.time()))
    return {
        "Content-Type": "application/json",
        "X-Client-Id": cliente,
        "X-Timestamp": ts,
        "X-Signature": f"sha256={firma or firmar(cuerpo, ts, cliente)}",
    }


async def test_firma_valida_crea_ticket(
    cliente: httpx.AsyncClient,
    repo: RepositorioFalso,
    eventos: list[str],
) -> None:
    cuerpo = payload()
    respuesta = await cliente.post(
        "/api/webhooks/tickets",
        content=cuerpo,
        headers=cabeceras(cuerpo),
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["titulo"] == "Ticket desde webhook"
    assert len(repo.tickets) == 1
    assert eventos == ["ticket.creado"]


async def test_firma_invalida_devuelve_401(
    cliente: httpx.AsyncClient,
    repo: RepositorioFalso,
) -> None:
    cuerpo = payload()
    respuesta = await cliente.post(
        "/api/webhooks/tickets",
        content=cuerpo,
        headers=cabeceras(cuerpo, firma="0" * 64),
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "firma_invalida"
    assert repo.tickets == {}


async def test_timestamp_viejo_devuelve_401(cliente: httpx.AsyncClient) -> None:
    cuerpo = payload()
    viejo = str(int(time.time()) - 400)
    respuesta = await cliente.post(
        "/api/webhooks/tickets",
        content=cuerpo,
        headers=cabeceras(cuerpo, timestamp=viejo),
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "timestamp_expirado"


async def test_payload_malformado_devuelve_422(cliente: httpx.AsyncClient) -> None:
    cuerpo = "{esto no es json"
    respuesta = await cliente.post(
        "/api/webhooks/tickets",
        content=cuerpo,
        headers=cabeceras(cuerpo),
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "payload_invalido"


async def test_campo_invalido_devuelve_422(cliente: httpx.AsyncClient) -> None:
    cuerpo = json.dumps({"titulo": "ab", "descripcion": "x"}, separators=(",", ":"))
    respuesta = await cliente.post(
        "/api/webhooks/tickets",
        content=cuerpo,
        headers=cabeceras(cuerpo),
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "payload_invalido"


async def test_event_id_repetido_es_idempotente(
    cliente: httpx.AsyncClient,
    repo: RepositorioFalso,
    eventos: list[str],
) -> None:
    cuerpo = payload("evt_repetido_0001")

    primera = await cliente.post(
        "/api/webhooks/tickets",
        content=cuerpo,
        headers=cabeceras(cuerpo),
    )
    segunda = await cliente.post(
        "/api/webhooks/tickets",
        content=cuerpo,
        headers=cabeceras(cuerpo),
    )

    assert primera.status_code == 201
    assert segunda.status_code == 200
    assert primera.json()["id"] == segunda.json()["id"]
    assert len(repo.tickets) == 1
    assert eventos == ["ticket.creado"]
