"""Logging estructurado en JSON, apto para agregadores."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

_CAMPOS_EXTRA = (
    "request_id",
    "metodo",
    "ruta",
    "status",
    "duracion_ms",
    "cliente_id",
    "event_id",
    "motivo",
)


class FormateadorJSON(logging.Formatter):
    """Serializa cada registro como una linea JSON.

    Los campos de contexto viajan en ``extra`` y se incluyen solo si existen:
    un log sin request_id no inventa el campo.
    """

    def format(self, record: logging.LogRecord) -> str:
        datos: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "nivel": record.levelname,
            "logger": record.name,
            "mensaje": record.getMessage(),
        }
        for campo in _CAMPOS_EXTRA:
            valor = getattr(record, campo, None)
            if valor is not None:
                datos[campo] = valor
        if record.exc_info:
            datos["excepcion"] = self.formatException(record.exc_info)
        return json.dumps(datos, ensure_ascii=False, default=str)


def configurar_logging(nivel: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(FormateadorJSON())

    raiz = logging.getLogger()
    raiz.handlers.clear()
    raiz.addHandler(handler)
    raiz.setLevel(nivel)

    # El middleware registra cada peticion; el access log de uvicorn duplica.
    logging.getLogger("uvicorn.access").disabled = True


def obtener_logger(nombre: str) -> logging.Logger:
    return logging.getLogger(nombre)
