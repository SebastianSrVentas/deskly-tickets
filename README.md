# Deskly - Sistema de tickets de soporte

Prototipo full-stack de gestion de tickets con maquina de estados, ingesta por
webhook firmado, actualizaciones en tiempo real por WebSocket y detalle con
renderizado en servidor.

Prueba tecnica: el codigo esta escrito para poder defenderlo linea por linea.
Las decisiones y el uso de herramientas estan documentados en `DECISIONES.md`.

## Stack

| Capa | Tecnologia |
|---|---|
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind 4 |
| Backend | FastAPI, Pydantic v2, Uvicorn, Python 3.14 |
| Base de datos | MongoDB 8 (PyMongo async) |
| Mensajeria | Redis 8.4 (Pub/Sub y Streams) |
| Infraestructura | Docker Compose, red interna, healthchecks |
| Observabilidad | Prometheus, Grafana, cAdvisor (perfil opcional) |
| Tests | pytest, pytest-asyncio, httpx |
| CI | GitHub Actions |

## Arranque

Requisitos: Docker Desktop con Compose v2. No hace falta Python ni Node en el
host: todo corre en contenedores.

```bash
git clone https://github.com/SebastianSrVentas/deskly-tickets.git
cd deskly-tickets
cp .env.example .env
docker compose up --build
```

Servicios:

| URL | Servicio |
|---|---|
| http://localhost:3000 | Frontend |
| http://localhost:8000/docs | API (OpenAPI / Swagger) |
| http://localhost:8000/api/health | Liveness |
| http://localhost:8000/api/health/ready | Readiness (Mongo y Redis) |
| http://localhost:8000/metrics | Metricas Prometheus |

Verificacion en 30 segundos:

```bash
curl -fsS http://localhost:8000/api/health
curl -fsS http://localhost:8000/api/health/ready
curl -fsS http://localhost:3000 > /dev/null && echo "frontend ok"
```

### Datos de ejemplo

Con `SEED_ON_START=true` (valor por defecto) el backend siembra 12 tickets
variados cuando la coleccion esta vacia. Es idempotente: el documento
`meta/seed_v1` impide duplicar en reinicios o con varias replicas, y el seed
solo corre si `count_documents({}) == 0`.

Para arrancar con la base vacia:

```bash
SEED_ON_START=false docker compose up --build
```

Observabilidad opcional (no participa en el arranque evaluado):

```bash
docker compose --profile obs up --build
```

Grafana queda en http://localhost:3001 (usuario `admin`, password
`GRAFANA_PASSWORD`), Prometheus en http://localhost:9090.

## Arquitectura

```
                    red interna: deskly_net (DNS por servicio)

  navegador
     |  HTTP :3000            HTTP :8000
     v                         v
  frontend:3000 ----------> backend:8000 ----------> mongo:27017
   (Next SSR)                (FastAPI)                 (interno)
                                  |
                                  +--> redis:6379 (interno)
                                  |      +- PUBLISH deskly:eventos  -> WebSockets
                                  |      +- XADD    deskly:cola     -> worker
                                  |
                              worker ---> mongo:auditoria
```

- Solo se publican `3000` y `8000`. MongoDB y Redis viven en la red interna.
- El backend es stateless: puede escalar a varias replicas. Los eventos se
  distribuyen por Redis Pub/Sub para que un cambio hecho en una replica llegue
  a los clientes conectados a otra.
- Redis no es fuente de verdad. La escritura en MongoDB es sincrona; la cola y
  los eventos son efectos que pueden reintentarse.

### Flujo de un ticket

1. `POST /api/tickets` valida con Pydantic y escribe en MongoDB.
2. Responde `201` con el ticket y su `id`.
3. Publica `ticket.creado` en Redis Pub/Sub para los WebSockets.
4. Encola el evento en un Redis Stream para trabajo asincrono con ack.

El ticket ya existe cuando se publica el evento. Si Redis falla, la respuesta
HTTP sigue siendo valida y se incrementa `deskly_eventos_fallidos_total`.

### Cola y worker

El servicio `worker` usa la misma imagen que el backend y consume
`deskly:cola` con el consumer group `deskly-workers`.

- Procesa cada evento y confirma con `XACK`.
- Si el manejador falla, el mensaje queda en el PEL y se reintenta con
  `XAUTOCLAIM` cuando el consumidor lleva mas de 60 s sin confirmarlo.
- Tras 3 intentos se mueve a `deskly:cola:muertos`.
- La auditoria en MongoDB es idempotente por `event_id`.

El backend nunca espera al worker: primero escribe en MongoDB y responde.

## API

| Metodo | Ruta | Descripcion |
|---|---|---|
| POST | `/api/tickets` | Crea un ticket en estado `abierto` |
| GET | `/api/tickets` | Lista paginada; filtros `estado`, `prioridad`, `q` |
| GET | `/api/tickets/{id}` | Detalle |
| PATCH | `/api/tickets/{id}` | Actualiza titulo, descripcion, prioridad, asignado |
| POST | `/api/tickets/{id}/transicion` | Cambia el estado |
| POST | `/api/tickets/{id}/comentarios` | Agrega un comentario |
| POST | `/api/webhooks/tickets` | Ingesta externa con HMAC |
| WS | `/ws/tickets` | Eventos en vivo |

La maquina de estados vive en `backend/app/domain/state_machine.py`:

```
abierto -> en_progreso -> resuelto -> cerrado
                             +------> abierto   (reabrir)
```

`PATCH` no acepta `estado`: con `extra="forbid"` devuelve 422. El estado solo
cambia por `/transicion`, y una transicion invalida devuelve `409` con las
transiciones permitidas en `detalles`.

## Webhook

`POST /api/webhooks/tickets`

Headers:

```
X-Client-Id: crm_acme
X-Timestamp: 1762819200
X-Signature: sha256=<hex>
X-Request-Id: <opcional>
```

La firma cubre `timestamp.client_id.body`, no solo el body. Firmar solo el body
permite reutilizar una captura; incluir el timestamp y el client_id ata la firma
a un cliente y a una ventana de 300 segundos.

Reglas:

- Firma ausente o incorrecta -> `401 firma_invalida`.
- Timestamp fuera de la ventana -> `401 timestamp_expirado`.
- JSON malformado o campos invalidos -> `422 payload_invalido`.
- `event_id` repetido -> `200` con el ticket original (idempotencia).
- Cuerpo mayor a `WEBHOOK_MAX_BODY_BYTES` -> `413`.

Modos de configuracion:

- `WEBHOOK_CLIENTES` vacio: se usa `WEBHOOK_SECRET` para cualquier
  `X-Client-Id`. Es el modo simple del `.env.example`.
- `WEBHOOK_CLIENTES` con JSON: solo los clientes listados, cada uno con su
  secreto. Se acepta una lista por cliente para rotar sin downtime:
  `{"crm_acme": ["nuevo", "anterior"]}`.

### Probar el webhook a mano

Opcion 1, script incluido (calcula timestamp, firma y curl):

```bash
python scripts/firmar_webhook.py --cliente crm_acme --secreto "$WEBHOOK_SECRET"
```

Copia el `curl` que imprime y ejecutalo. Para probar idempotencia, repite el
mismo comando con `--event-id evt_demo_0001` dos veces: la primera responde
`201` y la segunda `200` con el mismo `id`.

Opcion 2, sin script:

```bash
TS=$(date +%s)
BODY='{"titulo":"Ticket externo","descripcion":"Prueba manual","prioridad":"alta"}'
FIRMA=$(printf '%s.%s.%s' "$TS" "crm_acme" "$BODY" \
  | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -hex | sed 's/^.* //')

curl -i -X POST http://localhost:8000/api/webhooks/tickets \
  -H "Content-Type: application/json" \
  -H "X-Client-Id: crm_acme" \
  -H "X-Timestamp: $TS" \
  -H "X-Signature: sha256=$FIRMA" \
  --data "$BODY"
```

Prueba de rechazo: cambia un caracter del body sin recalcular la firma y repite.
Debe responder `401 firma_invalida`.

## WebSocket

`ws://localhost:8000/ws/tickets`

- Emite `ticket.creado`, `ticket.actualizado` y `ticket.comentado`.
- Cada evento incluye `tipo`, `event_id`, `ticket_id`, `ocurrido_en` y
  `datos` con el ticket completo.
- `?ticket_id=<id>` limita la suscripcion a ese ticket (bonus). La bandeja se
  suscribe sin filtro; el detalle usa el filtro.
- Al conectar envia `{"tipo":"conectado"}`. Acepta `ping` y responde `pong`.
- Si un cliente se desconecta, se elimina del registro y deja de recibir
  mensajes. El listener global sigue vivo para el resto.
- El frontend reconecta con backoff exponencial (1, 2, 4 ... 30 s) y muestra
  `Conectado`, `Desconectado` o `Reconectando`.

## Frontend

| Ruta | Tipo | Contenido |
|---|---|---|
| `/` | Server Component | bandeja con KPIs, filtros por URL, tabla y paginacion |
| `/tickets/[id]` | Server Component | detalle, hilo de comentarios y acciones de estado |

- Los filtros viven en la URL (`?estado=abierto&prioridad=alta&pagina=2`), asi
  el boton atras funciona y el servidor renderiza el resultado.
- `notFound()` devuelve 404 real para un id inexistente.
- Estados de UI separados: skeleton (`components/TablaSkeleton.tsx`), vacio y
  `app/error.tsx` con reintento.
- `hooks/useTicketStream.ts` es el hook propio: reconexion, limpieza en
  `useEffect` y filtro por ticket.
- `components/HiloComentarios.tsx` hace la UI optimista: el comentario aparece
  antes de la respuesta y se revierte con mensaje de error si el POST falla. La
  respuesta del POST trae el ticket completo, asi que se reemplaza el temporal
  por los datos reales sin parpadeo.
- Tipos generados desde OpenAPI: `npm run tipos` escribe `types/api.d.ts` con
  `openapi-typescript`; `types/ticket.ts` deriva de ahi. El archivo generado se
  versiona para que el build no dependa del backend levantado.
- `components/LiveTickets.tsx` conecta el hook con `router.refresh()`. Next
  revalida el Server Component y actualiza la UI sin recargar la pagina; el
  debounce de 300 ms evita una revalidacion por cada evento de una rafaga.
- SSR dentro de Docker usa `API_URL_INTERNA=http://backend:8000`; el navegador
  usa `NEXT_PUBLIC_API_URL=http://localhost:8000`. Usar la misma URL para ambos
  rompe el SSR, porque dentro del contenedor `localhost` es Next, no el backend.

## Base de datos

MongoDB. La justificacion y la alternativa descartada estan en `DECISIONES.md`.

Indices:

| Indice | Motivo |
|---|---|
| `(estado, creado_en)` | listado filtrado por estado y ordenado por fecha |
| `(prioridad, creado_en)` | filtro por prioridad con el mismo orden |
| `event_id` unique sparse | idempotencia del webhook; los tickets de la API no tienen `event_id` |

## Tests

```bash
cd backend
uv run pytest
```

Cobertura actual (17 tests):

- Maquina de estados: transiciones validas, invalidas, reapertura y estado
  terminal.
- Webhook: firma valida, firma invalida, timestamp viejo, JSON malformado,
  campo invalido e idempotencia por `event_id`.

Los tests no levantan Mongo ni Redis: el repositorio se reemplaza por un fake y
la publicacion se monkeypatchea. El flujo real se verifico a mano contra los
contenedores (ver `DECISIONES.md`).

## Tiempo invertido

Aproximadamente **32 horas de trabajo efectivo** (estimacion), repartidas asi:

| Fase | Horas |
|---|---|
| Diseno de arquitectura y discusion de decisiones | 4 |
| Backend: dominio, persistencia, REST, observabilidad | 10 |
| Webhook, WebSocket y worker | 5 |
| Frontend: SSR, dashboard, detalle y hook en vivo | 7 |
| Docker, CI, pruebas manuales y correcciones | 2 |
| Documentacion | 2 |
| Bonus: seed, UI optimista y tipos generados | 2 |

## Que queda fuera y por que

- **Despliegue en nube**: Amplify para Next, ECS/Fargate para FastAPI, Atlas y
  ElastiCache quedan documentados como ruta futura. El camino evaluado es
  `docker compose up --build` local; implementar la nube antes de cerrar el
  obligatorio habria consumido el tiempo de las pruebas.
- **Tests de integracion con Mongo y Redis reales**: los tests obligatorios son
  unitarios. El flujo completo se verifico con `curl`, `httpx` y un cliente
  WebSocket contra los contenedores.
- **Seed con datos de negocio reales**: el seed incluido es de demostracion
  (12 tickets ficticios). Cargar datos de un cliente exigiria un importador y
  reglas de privacidad que no forman parte del brief.

## Estado del proyecto

- [x] Modelo Ticket con todos los campos del brief
- [x] Endpoints REST con paginacion y filtro
- [x] Maquina de estados con reapertura y errores claros
- [x] Webhook HMAC-SHA256 con anti-replay, idempotencia y rate limiting
- [x] WebSocket con eventos, filtro por ticket y desconexion limpia
- [x] Dashboard SSR con filtros, paginacion y estados de UI
- [x] Detalle SSR con comentarios y botones de estado
- [x] Hook `useTicketStream` con reconexion y limpieza
- [x] Indicador de conexion conectado / desconectado / reconectando
- [x] MongoDB con indices justificados
- [x] Docker Compose con red interna, healthchecks y variables de entorno
- [x] Tests de maquina de estados y webhook
- [x] Dockerfiles multi-stage, CI con lint y tests
- [x] Reconexion automatica y suscripcion por ticket (bonus)
- [x] Seed idempotente de 12 tickets de ejemplo (bonus)
- [x] Comentarios con UI optimista y reversion (bonus)
- [x] Tipos TypeScript generados desde OpenAPI (bonus)
- [ ] Despliegue en nube: documentado como ruta futura
