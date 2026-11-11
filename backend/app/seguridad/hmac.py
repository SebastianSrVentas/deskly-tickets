"""Firma HMAC-SHA256 del webhook de ingesta.

El material firmado es ``timestamp.client_id.body``. Incluir el timestamp y el
client_id impide que una firma capturada se reutilice con otro cliente o fuera
de la ventana anti-replay.
"""

import hashlib
import hmac
import time

PREFIJO_FIRMA = "sha256="


def material_firma(timestamp: str, client_id: str, cuerpo: bytes) -> bytes:
    """Bytes exactos que el cliente y el servidor deben firmar."""
    return f"{timestamp}.{client_id}.".encode() + cuerpo


def calcular_firma(secreto: str, timestamp: str, client_id: str, cuerpo: bytes) -> str:
    """Devuelve el hex HMAC-SHA256. El prefijo ``sha256=`` lo agrega el header."""
    return hmac.new(
        secreto.encode("utf-8"),
        material_firma(timestamp, client_id, cuerpo),
        hashlib.sha256,
    ).hexdigest()


def normalizar_firma(firma: str) -> str:
    """Acepta ``sha256=<hex>`` o ``<hex>``; el brief no fija el prefijo."""
    limpia = firma.strip().lower()
    if limpia.startswith(PREFIJO_FIRMA):
        return limpia[len(PREFIJO_FIRMA) :]
    return limpia


def verificar_firma(
    secreto: str,
    timestamp: str,
    client_id: str,
    cuerpo: bytes,
    firma: str,
) -> bool:
    """Compara en tiempo constante para no filtrar el secreto por timing."""
    esperada = calcular_firma(secreto, timestamp, client_id, cuerpo)
    return hmac.compare_digest(esperada, normalizar_firma(firma))


def timestamp_valido(
    timestamp: str,
    tolerancia_segundos: int,
    ahora: float | None = None,
) -> bool:
    """True si el timestamp esta dentro de la ventana anti-replay."""
    try:
        valor = int(timestamp)
    except (TypeError, ValueError):
        return False

    referencia = time.time() if ahora is None else ahora
    return abs(referencia - valor) <= tolerancia_segundos


def desfase_segundos(timestamp: str, ahora: float | None = None) -> float | None:
    """Segundos entre el reloj del cliente y el del servidor, para metricas."""
    try:
        valor = int(timestamp)
    except (TypeError, ValueError):
        return None

    referencia = time.time() if ahora is None else ahora
    return referencia - valor
