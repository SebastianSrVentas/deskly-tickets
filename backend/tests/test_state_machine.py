"""Tests de la maquina de estados.

Es dominio puro: no necesita Mongo, Redis ni FastAPI. Un cambio en las
transiciones rompe estos tests antes de llegar al endpoint.
"""

import pytest

from app.domain.state_machine import TRANSICIONES, transiciones_permitidas, validar_transicion
from app.errores import TransicionInvalida
from app.models.ticket import Estado


@pytest.mark.parametrize(
    ("actual", "destino"),
    [
        (Estado.ABIERTO, Estado.EN_PROGRESO),
        (Estado.EN_PROGRESO, Estado.RESUELTO),
        (Estado.RESUELTO, Estado.CERRADO),
        (Estado.RESUELTO, Estado.ABIERTO),
    ],
)
def test_transiciones_validas(actual: Estado, destino: Estado) -> None:
    validar_transicion(actual, destino)


@pytest.mark.parametrize(
    ("actual", "destino"),
    [
        (Estado.ABIERTO, Estado.RESUELTO),
        (Estado.ABIERTO, Estado.CERRADO),
        (Estado.EN_PROGRESO, Estado.ABIERTO),
        (Estado.CERRADO, Estado.ABIERTO),
        (Estado.CERRADO, Estado.EN_PROGRESO),
    ],
)
def test_transiciones_invalidas(actual: Estado, destino: Estado) -> None:
    with pytest.raises(TransicionInvalida) as excinfo:
        validar_transicion(actual, destino)

    error = excinfo.value
    assert error.status == 409
    assert error.codigo == "transicion_invalida"
    assert error.detalles["estado_actual"] == actual.value
    assert error.detalles["estado_solicitado"] == destino.value


def test_cerrado_es_terminal() -> None:
    assert transiciones_permitidas(Estado.CERRADO) == frozenset()
    assert TRANSICIONES[Estado.CERRADO] == frozenset()


def test_resuelto_permite_reabrir_y_cerrar() -> None:
    assert transiciones_permitidas(Estado.RESUELTO) == frozenset(
        {Estado.CERRADO, Estado.ABIERTO}
    )
