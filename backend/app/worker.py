"""Punto de entrada del worker de la cola.

Se ejecuta con la misma imagen que el backend y distinto comando:

    python -m app.worker
"""

import asyncio
import contextlib
import signal

from app.cola.consumidor import ConfiguracionConsumidor, Consumidor
from app.cola.manejadores import manejar_evento
from app.config import get_settings
from app.db import basedatos
from app.observabilidad.logging import configurar_logging, obtener_logger
from app.redis import conexion_redis

logger = obtener_logger(__name__)


async def main() -> None:
    settings = get_settings()
    configurar_logging(settings.log_level)

    await basedatos.conectar(settings)
    # El worker usa XREADGROUP con bloqueo de 5 s: el socket debe esperar mas
    # que el bloqueo o cada lectura termina en TimeoutError.
    await conexion_redis.conectar(settings, socket_timeout=10)

    config = ConfiguracionConsumidor()
    consumidor = Consumidor(conexion_redis.requerido(), manejar_evento, config)
    detener = asyncio.Event()

    loop = asyncio.get_running_loop()
    for senal in (signal.SIGTERM, signal.SIGINT):
        # Windows no soporta add_signal_handler para SIGTERM.
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(senal, detener.set)

    logger.info("worker_iniciado", extra={"motivo": config.nombre})
    try:
        await consumidor.ejecutar(detener)
    finally:
        await conexion_redis.cerrar()
        await basedatos.cerrar()
        logger.info("worker_detenido")


if __name__ == "__main__":
    asyncio.run(main())
