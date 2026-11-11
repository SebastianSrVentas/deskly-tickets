"""Datos de ejemplo para que el dashboard no arranque vacio.

Se aplica una sola vez por base. El documento de la coleccion ``meta`` actua
como candado: si dos replicas arrancan a la vez, solo una inserta. Si la
insercion falla, el candado se borra para permitir el reintento en el proximo
arranque.

Para arrancar sin datos: ``SEED_ON_START=false``.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from pymongo.errors import DuplicateKeyError

from app.db import basedatos
from app.observabilidad.logging import obtener_logger

logger = obtener_logger(__name__)

META_SEED = "seed_v1"


def _comentario(autor: str, texto: str, cuando: datetime) -> dict[str, Any]:
    return {
        "id": f"seed-{autor.lower().replace(' ', '-')}-{int(cuando.timestamp())}",
        "autor": autor,
        "texto": texto,
        "creado_en": cuando,
    }


TICKETS: list[dict[str, Any]] = [
    {
        "titulo": "No puedo iniciar sesion con mi cuenta corporativa",
        "descripcion": "El login devuelve credenciales invalidas aunque la contrasena es correcta.",
        "prioridad": "alta",
        "estado": "abierto",
        "asignado_a": "Ana Torres",
        "dias": 0,
        "comentarios": [
            ("Ana Torres", "Revise el registro de accesos y la cuenta no esta bloqueada.", 2),
        ],
    },
    {
        "titulo": "Error 500 al exportar el reporte mensual",
        "descripcion": "La exportacion en PDF falla siempre en el mismo mes. En CSV funciona.",
        "prioridad": "critica",
        "estado": "en_progreso",
        "asignado_a": "Luis Pardo",
        "dias": 0,
        "comentarios": [
            ("Luis Pardo", "Reproducido en local. El fallo esta en el generador de tablas.", 3),
            ("Marta Ruiz", "El cliente necesita el reporte hoy.", 1),
        ],
    },
    {
        "titulo": "Solicitud de acceso al panel de facturacion",
        "descripcion": "Necesito permisos de lectura para conciliar pagos del trimestre.",
        "prioridad": "media",
        "estado": "abierto",
        "asignado_a": None,
        "dias": 1,
        "comentarios": [],
    },
    {
        "titulo": "El correo de restablecimiento no llega",
        "descripcion": "Se solicito tres veces y no aparece en la bandeja ni en spam.",
        "prioridad": "alta",
        "estado": "en_progreso",
        "asignado_a": "Marta Ruiz",
        "dias": 1,
        "comentarios": [
            ("Marta Ruiz", "El proveedor reporta rebotes. Revisando la lista de supresion.", 2),
        ],
    },
    {
        "titulo": "La carga de archivos se queda en 99%",
        "descripcion": "Archivos de mas de 20 MB se quedan casi completos y nunca terminan.",
        "prioridad": "critica",
        "estado": "abierto",
        "asignado_a": "Carlos Nunez",
        "dias": 2,
        "comentarios": [],
    },
    {
        "titulo": "Cambiar el plan de la suscripcion",
        "descripcion": "Solicitud para pasar del plan mensual al anual con las mismas condiciones.",
        "prioridad": "baja",
        "estado": "resuelto",
        "asignado_a": "Ana Torres",
        "dias": 2,
        "comentarios": [
            ("Ana Torres", "Cambio aplicado y confirmado por el cliente.", 4),
        ],
    },
    {
        "titulo": "Faltan datos en el historial de pedidos",
        "descripcion": "Los pedidos de la ultima semana no muestran la direccion de envio.",
        "prioridad": "media",
        "estado": "abierto",
        "asignado_a": None,
        "dias": 3,
        "comentarios": [],
    },
    {
        "titulo": "Error de validacion al guardar la direccion fiscal",
        "descripcion": "El formulario rechaza el codigo postal aunque tiene el formato correcto.",
        "prioridad": "alta",
        "estado": "resuelto",
        "asignado_a": "Luis Pardo",
        "dias": 3,
        "comentarios": [
            ("Luis Pardo", "Se corrigio la expresion regular del codigo postal.", 5),
        ],
    },
    {
        "titulo": "El buscador no encuentra clientes por RFC",
        "descripcion": "Al buscar por RFC aparece sin resultados incluso con clientes activos.",
        "prioridad": "media",
        "estado": "abierto",
        "asignado_a": "Marta Ruiz",
        "dias": 4,
        "comentarios": [],
    },
    {
        "titulo": "Solicitud de factura con datos actualizados",
        "descripcion": "Se requiere reemitir la factura con la razon social nueva.",
        "prioridad": "baja",
        "estado": "cerrado",
        "asignado_a": "Carlos Nunez",
        "dias": 5,
        "comentarios": [
            ("Carlos Nunez", "Factura reemitida y enviada por correo.", 6),
        ],
    },
    {
        "titulo": "La app movil cierra sesion sola",
        "descripcion": "Despues de unos minutos en segundo plano la sesion expira sin aviso.",
        "prioridad": "alta",
        "estado": "cerrado",
        "asignado_a": "Ana Torres",
        "dias": 6,
        "comentarios": [
            ("Ana Torres", "Se ajusto el tiempo de refresco del token.", 8),
        ],
    },
    {
        "titulo": "Duda sobre el limite de usuarios del plan",
        "descripcion": "Queremos saber si el plan actual permite agregar dos usuarios mas.",
        "prioridad": "baja",
        "estado": "cerrado",
        "asignado_a": None,
        "dias": 7,
        "comentarios": [],
    },
]


def _historial(estado: str, creado: datetime, actualizado: datetime) -> list[dict[str, Any]]:
    """Historial coherente con el estado final del ticket de ejemplo."""
    eventos: list[dict[str, Any]] = [
        {
            "anterior": None,
            "nuevo": "abierto",
            "motivo": "seed",
            "en": creado,
        }
    ]
    if estado in {"en_progreso", "resuelto", "cerrado"}:
        eventos.append(
            {
                "anterior": "abierto",
                "nuevo": "en_progreso",
                "motivo": "seed",
                "en": creado + timedelta(hours=2),
            }
        )
    if estado in {"resuelto", "cerrado"}:
        eventos.append(
            {
                "anterior": "en_progreso",
                "nuevo": "resuelto",
                "motivo": "seed",
                "en": actualizado - timedelta(hours=1),
            }
        )
    if estado == "cerrado":
        eventos.append(
            {
                "anterior": "resuelto",
                "nuevo": "cerrado",
                "motivo": "seed",
                "en": actualizado,
            }
        )
    return eventos


async def sembrar_si_vacio() -> int:
    """Inserta los tickets de ejemplo si la base esta vacia.

    Devuelve cuantos tickets inserto. Es idempotente por el documento
    ``meta/seed_v1`` y por ``count_documents``.
    """
    if basedatos.db is None:
        return 0

    coleccion = basedatos.coleccion("tickets")
    if await coleccion.count_documents({}) > 0:
        return 0

    meta = basedatos.coleccion("meta")
    ahora = datetime.now(UTC)
    try:
        await meta.insert_one({"_id": META_SEED, "aplicado_en": ahora})
    except DuplicateKeyError:
        return 0

    documentos: list[dict[str, Any]] = []
    for datos in TICKETS:
        creado = ahora - timedelta(days=datos["dias"], hours=len(documentos))
        actualizado = creado + timedelta(hours=3)
        comentarios = [
            _comentario(autor, texto, creado + timedelta(hours=horas))
            for autor, texto, horas in datos["comentarios"]
        ]
        documentos.append(
            {
                "titulo": datos["titulo"],
                "descripcion": datos["descripcion"],
                "prioridad": datos["prioridad"],
                "estado": datos["estado"],
                "asignado_a": datos["asignado_a"],
                "comentarios": comentarios,
                "historial": _historial(datos["estado"], creado, actualizado),
                "origen": {"tipo": "seed"},
                "creado_en": creado,
                "actualizado_en": actualizado,
            }
        )

    try:
        resultado = await coleccion.insert_many(documentos)
    except Exception:
        # Sin el candado, el proximo arranque puede reintentar el seed.
        await meta.delete_one({"_id": META_SEED})
        raise

    logger.info("seed_aplicado", extra={"tickets": len(resultado.inserted_ids)})
    return len(resultado.inserted_ids)
