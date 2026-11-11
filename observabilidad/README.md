# Observabilidad

Perfil opcional. No forma parte del camino critico de arranque.

```bash
docker compose --profile obs up --build
```

## Componentes

| Servicio | Puerto | Funcion |
|---|---|---|
| Prometheus | 9090 | recoleccion de metricas y evaluacion de alertas |
| Grafana | 3001 | dashboards provisionados como codigo |
| cAdvisor | 8080 | CPU y memoria por contenedor |
| redis-exporter | 9121 | metricas de Redis |
| mongodb-exporter | 9216 | metricas de MongoDB |

## Metricas propias del backend

| Metrica | Tipo | Etiquetas |
|---|---|---|
| `deskly_tickets_creados_total` | counter | `origen` |
| `deskly_transiciones_total` | counter | `destino` |
| `deskly_webhook_total` | counter | `cliente`, `resultado` |
| `deskly_ratelimit_degradado_total` | counter | - |
| `deskly_eventos_fallidos_total` | counter | `canal` |
| `deskly_cola_pendientes` | gauge | - |
| `deskly_webhook_desfase_segundos` | histogram | - |

Las metricas HTTP (`http_requests_total`, `http_request_duration_seconds`)
las genera `prometheus-fastapi-instrumentator`.

## Alertas

Definidas en `prometheus/alertas.yml`:

- Backend caido.
- Mas de 5% de respuestas 5xx durante 5 minutos.
- Latencia p95 mayor a 1 segundo durante 5 minutos.
- Redis o MongoDB caidos.
- Cola con mas de 100 mensajes pendientes durante 10 minutos.

## Seguridad

- Grafana no permite registro publico.
- La contrasena se toma de `GRAFANA_PASSWORD`; el valor por defecto `admin`
  es solo para desarrollo local.
- En produccion, Prometheus y Grafana no deben publicarse a internet.
