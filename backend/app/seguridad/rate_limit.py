"""Rate limiting distribuido con token bucket atomico en Redis.

Se usa un script Lua para que leer, recalcular y escribir el bucket ocurra en
una sola operacion atomica. Un GET seguido de SET permite que dos replicas
consuman el mismo token.
"""

from dataclasses import dataclass

from redis.exceptions import RedisError

from app.observabilidad.metricas import RATELIMIT_DEGRADADO
from app.redis import conexion_redis

_SCRIPT_TOKEN_BUCKET = """
local t = redis.call('TIME')
local ahora = tonumber(t[1]) + tonumber(t[2]) / 1000000

local datos = redis.call('HMGET', KEYS[1], 'tokens', 'ts')
local tokens = tonumber(datos[1])
local ts = tonumber(datos[2])

local capacidad = tonumber(ARGV[1])
local tasa = tonumber(ARGV[2])
local costo = tonumber(ARGV[3])

if tokens == nil then tokens = capacidad end
if ts == nil then ts = ahora end

local delta = math.max(0, ahora - ts)
tokens = math.min(capacidad, tokens + delta * tasa)

local permitido = 0
if tokens >= costo then
  tokens = tokens - costo
  permitido = 1
end

redis.call('HSET', KEYS[1], 'tokens', tokens, 'ts', ahora)
redis.call('EXPIRE', KEYS[1], math.ceil(capacidad / tasa) + 60)

return {permitido, math.floor(tokens), capacidad}
"""


@dataclass(frozen=True)
class ResultadoLimite:
    permitido: bool
    restantes: int
    limite: int
    reintentar_en_segundos: float = 0.0


async def consumir(
    clave: str,
    capacidad: int,
    tasa_por_segundo: int,
    costo: int = 1,
) -> ResultadoLimite:
    """Consume un token del bucket.

    Si Redis no responde se permite la solicitud (fail-open) y se incrementa
    una metrica: tumbar el servicio por el limitador es peor que servir de mas.
    """
    cliente = conexion_redis.cliente
    if cliente is None:
        # Redis no estaba disponible al arrancar: fail-open, igual que un
        # timeout. Tumbar el webhook por el limitador seria peor.
        RATELIMIT_DEGRADADO.inc()
        return ResultadoLimite(permitido=True, restantes=capacidad, limite=capacidad)

    try:
        permitido, restantes, limite = await cliente.eval(
            _SCRIPT_TOKEN_BUCKET,
            1,
            clave,
            capacidad,
            tasa_por_segundo,
            costo,
        )
    except RedisError:
        RATELIMIT_DEGRADADO.inc()
        return ResultadoLimite(permitido=True, restantes=capacidad, limite=capacidad)

    autorizado = bool(permitido)
    reintentar = 0.0
    if not autorizado:
        reintentar = max(0.0, (costo - restantes) / tasa_por_segundo)

    return ResultadoLimite(
        permitido=autorizado,
        restantes=int(restantes),
        limite=int(limite),
        reintentar_en_segundos=round(reintentar, 3),
    )
