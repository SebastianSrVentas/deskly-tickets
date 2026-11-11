"""Maquina de estados del ticket.

Dominio puro: no importa FastAPI ni MongoDB. Por eso se puede probar sin
levantar nada y es el bloque que se defiende en entrevista.
"""

from app.errores import TransicionInvalida
from app.models.ticket import Estado

TRANSICIONES: dict[Estado, frozenset[Estado]] = {
    Estado.ABIERTO: frozenset({Estado.EN_PROGRESO}),
    Estado.EN_PROGRESO: frozenset({Estado.RESUELTO}),
    # Reabrir vuelve a "abierto": no se crea un estado "reabierto" que
    # duplicaria la semantica. El historial guarda el motivo.
    Estado.RESUELTO: frozenset({Estado.CERRADO, Estado.ABIERTO}),
    Estado.CERRADO: frozenset(),
}


def transiciones_permitidas(actual: Estado) -> frozenset[Estado]:
    return TRANSICIONES[actual]


def validar_transicion(actual: Estado, destino: Estado) -> None:
    permitidas = transiciones_permitidas(actual)
    if destino not in permitidas:
        raise TransicionInvalida(
            mensaje=f"No se puede pasar de '{actual.value}' a '{destino.value}'",
            detalles={
                "estado_actual": actual.value,
                "estado_solicitado": destino.value,
                "transiciones_permitidas": sorted(estado.value for estado in permitidas),
            },
        )
