"""Metricas de negocio expuestas a Prometheus."""

from prometheus_client import Counter, Gauge, Histogram

TICKETS_CREADOS = Counter(
    "deskly_tickets_creados_total",
    "Tickets creados, separados por origen",
    ["origen"],
)

TRANSICIONES = Counter(
    "deskly_transiciones_total",
    "Transiciones de estado aplicadas",
    ["destino"],
)

WEBHOOK = Counter(
    "deskly_webhook_total",
    "Solicitudes recibidas en el webhook",
    ["cliente", "resultado"],
)

RATELIMIT_DEGRADADO = Counter(
    "deskly_ratelimit_degradado_total",
    "Veces que el rate limit no pudo consultar Redis",
)

EVENTOS_FALLIDOS = Counter(
    "deskly_eventos_fallidos_total",
    "Eventos que no se pudieron publicar en Redis",
    ["canal"],
)

COLA_PENDIENTES = Gauge(
    "deskly_cola_pendientes",
    "Mensajes pendientes en el stream de trabajo",
)

DESFASE_WEBHOOK = Histogram(
    "deskly_webhook_desfase_segundos",
    "Diferencia entre el timestamp del cliente y el reloj del servidor",
    buckets=[-300, -60, -5, 0, 5, 60, 300],
)
