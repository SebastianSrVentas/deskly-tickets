# Recorrido del proyecto

Guia para demostrar Deskly y defender el codigo en la entrevista. Cada parada
dice que mostrar, que archivo mirar y que decision explicar.

## Antes de empezar

```bash
git clone https://github.com/SebastianSrVentas/deskly-tickets.git
cd deskly-tickets
cp .env.example .env
docker compose up --build
```

Verificar:

```bash
docker compose ps
curl -fsS http://localhost:8000/api/health/ready
curl -fsS http://localhost:3000 > /dev/null && echo "frontend ok"
```

Servicios esperados: `backend`, `frontend`, `mongo` y `redis` en `healthy`,
`worker` arriba. Solo 3000 y 8000 publicados.

## Guion de demo (7 minutos)

### 1. Bandeja

Abrir http://localhost:3000.

Mostrar: 12 tickets del seed, KPIs, filtros por estado, filtro por prioridad,
buscador y paginacion. La URL guarda los filtros (`?estado=abierto&prioridad=alta`).

Codigo: `frontend/app/page.tsx`, `components/FiltrosTickets.tsx`,
`components/TicketTabla.tsx`, `lib/api.ts`.

Que explicar: la pagina es un Server Component. El HTML llega renderizado; no
hay `useEffect` cargando la tabla. Los filtros se leen de `searchParams` y se
mandan al backend.

### 2. Detalle SSR

Abrir un ticket.

Mostrar: estado, prioridad, asignado, fechas, hilo de comentarios y botones de
transicion.

Codigo: `frontend/app/tickets/[id]/page.tsx`, `components/AccionesTicket.tsx`,
`components/HiloComentarios.tsx`.

Que explicar: `notFound()` corre en `generateMetadata`, antes del streaming, y
devuelve 404 real. Verificar:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/tickets/no-existe
```

### 3. Transicion valida e invalida

En el detalle, pasar de `abierto` a `en_progreso`.

Para la invalida, desde Swagger (`http://localhost:8000/docs`) o curl:

```bash
curl -s -X POST http://localhost:8000/api/tickets/<id>/transicion \
  -H 'Content-Type: application/json' \
  -d '{"estado_destino":"cerrado"}'
```

Mostrar `409 transicion_invalida` con `transiciones_permitidas: ["resuelto"]`.

Codigo: `backend/app/domain/state_machine.py`,
`backend/app/repositories/tickets.py` (metodo `transicionar`).

Que explicar: la maquina de estados es dominio puro, sin FastAPI ni Mongo. La
transicion usa `find_one_and_update({_id, estado: actual})`; si no matchea,
devuelve 409. `PATCH` no acepta `estado` por `extra="forbid"`.

### 4. Comentario optimista

Escribir un comentario y enviarlo.

Mostrar: aparece al instante con "Enviando...", luego queda confirmado. El
contador sube. Recargar y sigue ahi.

Codigo: `frontend/components/HiloComentarios.tsx`.

Que explicar: el comentario temporal entra en `useState` antes del POST. Si
falla, se filtra y se muestra error. Si responde, la respuesta trae el ticket
completo y reemplaza el temporal. `startTransition` solo envuelve el fetch.

### 5. Ticket nuevo en vivo

Abrir Swagger en otra pestana y crear un ticket, o:

```bash
curl -s -X POST http://localhost:8000/api/tickets \
  -H 'Content-Type: application/json' \
  -d '{"titulo":"Ticket en vivo","descripcion":"Sin recargar","prioridad":"critica"}'
```

Volver a la bandeja. La fila aparece sin recargar. El indicador dice
"Conectado".

Codigo: `backend/app/api/ws.py`, `frontend/hooks/useTicketStream.ts`,
`components/LiveTickets.tsx`.

Que explicar: el backend publica `ticket.creado` en Redis Pub/Sub; el listener
lo difunde a los WebSockets; el hook llama `router.refresh()` y Next revalida el
Server Component. No hay polling.

### 6. Webhook firmado

```bash
# Lee el secreto del cliente configurado en .env
python scripts/firmar_webhook.py --cliente crm_acme --secreto "<secreto>" \
  --event-id evt_demo_0001
```

Copiar el `curl` que imprime y ejecutarlo. Primera vez: `201`. Repetir el mismo
comando: `200` con el mismo `id`.

Cambiar un caracter del body sin recalcular la firma: `401 firma_invalida`.

Codigo: `backend/app/api/webhooks.py`, `backend/app/seguridad/hmac.py`,
`backend/app/models/webhook.py`, `scripts/firmar_webhook.py`.

Que explicar: la firma cubre `timestamp.client_id.body`, no solo el body. La
ventana es de 300 s. La idempotencia la garantiza el indice unique sparse en
`tickets.event_id`, no un `find_one` previo.

### 7. Worker y metricas

```bash
docker compose exec redis redis-cli XPENDING deskly:cola deskly-workers
docker compose logs --tail=20 worker
curl -s http://localhost:8000/metrics | grep deskly_
```

Mostrar: PEL 0, auditoria en Mongo con `cliente_id`, contadores por origen.

Codigo: `backend/app/cola/consumidor.py`, `backend/app/worker.py`,
`backend/app/observabilidad/metricas.py`.

Que explicar: `XACK` tras procesar, `XAUTOCLAIM` a los 60 s, tres intentos y
`deskly:cola:muertos`. La auditoria tiene indice unique por `event_id`.

## Flujo de una peticion

```
POST /api/tickets
  -> MiddlewareContexto (request-id, logs, metricas)
  -> FastAPI valida con TicketCrear (Pydantic v2)
  -> api/tickets.py: crear_ticket
  -> RepositorioTickets.crear
  -> MongoDB insert_one
  -> 201 con el ticket y su id
  -> publicar_evento("ticket.creado")
       -> PUBLISH deskly:eventos  (WebSocket)
       -> XADD    deskly:cola     (worker)
```

Si Redis falla, el ticket ya esta en Mongo y la respuesta sigue siendo 201. Se
incrementa `deskly_eventos_fallidos_total`.

## Mapa de codigo

| Archivo | Responsabilidad | Que defender |
|---|---|---|
| `backend/app/main.py` | App, lifespan, routers, health | Mongo obligatorio, Redis degradado, seed, listener WS |
| `backend/app/config.py` | Settings desde entorno | Nombres, validacion, `webhook_clientes` |
| `backend/app/db.py` | Cliente async e indices | `(estado, creado_en)`, `(prioridad, creado_en)`, `event_id` unique |
| `backend/app/models/ticket.py` | Pydantic v2 | `extra="forbid"`, `StrEnum`, `Annotated`, longitudes |
| `backend/app/domain/state_machine.py` | FSM pura | Transiciones y reapertura sin infraestructura |
| `backend/app/repositories/tickets.py` | Mongo | Transicion atomica, comentarios, idempotencia |
| `backend/app/api/tickets.py` | REST | 6 endpoints, metricas, publicacion de eventos |
| `backend/app/api/webhooks.py` | Ingesta | HMAC, replay, rate limit, 401/422/413 |
| `backend/app/api/ws.py` | WebSocket | Listener Pub/Sub, fan-out, filtro por ticket |
| `backend/app/seguridad/hmac.py` | Firma | Material firmado y `compare_digest` |
| `backend/app/seguridad/rate_limit.py` | Token bucket | Lua atomico, fail-open |
| `backend/app/cola/publicador.py` | Eventos | Dos canales, no romper la respuesta |
| `backend/app/cola/consumidor.py` | Worker | Consumer group, ack, reclamo, DLQ |
| `backend/app/seed.py` | Datos demo | Doble candado, idempotencia |
| `backend/app/observabilidad/` | Logs y metricas | JSON, request-id, contadores |
| `frontend/app/page.tsx` | Bandeja SSR | Filtros por URL, KPIs, paginacion |
| `frontend/app/tickets/[id]/page.tsx` | Detalle SSR | 404 real, comentarios, acciones |
| `frontend/hooks/useTicketStream.ts` | WS cliente | Reconexion, limpieza, filtro |
| `frontend/components/LiveTickets.tsx` | Puente RSC | `router.refresh()` con debounce |
| `frontend/components/HiloComentarios.tsx` | Comentarios | UI optimista y reversion |
| `frontend/lib/api.ts` | Cliente HTTP | URL interna vs publica, `no-store` |
| `frontend/types/ticket.ts` | Tipos | Derivados de `api.d.ts` |
| `docker-compose.yml` | Infra | Red interna, healthchecks, solo 3000/8000 |
| `backend/Dockerfile` | Imagen | Multi-stage, usuario `app`, healthcheck |

## Preguntas de defensa

**¿Por que MongoDB y no PostgreSQL?**
El ticket, sus comentarios y su historial se leen como un solo documento. No hay
JOINs ni transacciones multi-documento que justifiquen SQL. Si el producto
creciera a reportes relacionales, migraria.

**¿Por que 201 y no 202 si hay cola?**
Porque el cliente necesita el `id` para el detalle SSR y el test del webhook
espera el ticket creado. La cola maneja efectos reintentables, no la creacion.

**¿Que pasa si Redis se cae?**
La API sigue: el ticket se escribe en Mongo y la respuesta es 201. Se pierden
los eventos en vivo y el rate limit hace fail-open con metrica. `/ready` queda
en `degradado`, no en 503.

**¿Como evitas dos transiciones simultaneas?**
`find_one_and_update({_id, estado: actual})`. Si otra solicitud cambio el estado,
el filtro no matchea y se devuelve 409. No hay lectura-modificacion-escritura.

**¿Por que el PATCH no acepta estado?**
Para que no se salte la FSM. `extra="forbid"` devuelve 422 si llega `estado`; el
unico camino es `/transicion`.

**¿Que firma el webhook?**
`timestamp.client_id.body`. Firmar solo el body permite replay; dejar el
`client_id` fuera permite suplantarlo. `compare_digest` evita filtrar el secreto
por timing.

**¿Como garantizas idempotencia sin carrera?**
Indice unique sparse en `tickets.event_id`. Dos requests con el mismo evento:
una inserta, la otra recibe `DuplicateKeyError` y devuelve el ticket original con
200. Un `find_one` previo no basta.

**¿Como escala el WebSocket a varias replicas?**
Cada replica tiene su listener de Pub/Sub y su registro de conexiones. Un evento
publicado llega a todas; cada una lo entrega a sus clientes. No hay estado
compartido en memoria.

**¿Por que dos URLs para el frontend?**
Dentro del contenedor de Next, `localhost` es Next, no el backend. El SSR usa
`API_URL_INTERNA=http://backend:8000`; el navegador usa
`NEXT_PUBLIC_API_URL=http://localhost:8000`.

**¿Que dejaste fuera?**
Solo el despliegue en nube, documentado como ruta futura. El resto del
obligatorio y los 9 bonus estan implementados.

**¿Como verificaste que funciona?**
17 tests unitarios, flujo real con `curl`/`httpx`, cliente WebSocket, clone
limpio con `docker compose`, y CI en verde.

## Limitaciones conocidas

- El seed es de demostracion; no importa datos de negocio.
- Los tipos generados se actualizan a mano con `npm run tipos`; el CI no compara
  el contrato contra el backend.
- La UI optimista cubre comentarios, no transiciones (duplicar la FSM en el
  cliente no compensa).
- La observabilidad completa vive en el perfil `obs` y no es necesaria para el
  arranque evaluado.

## Fuentes

- `backend/`, `frontend/`, `docker-compose.yml`
- `README.md`, `DECISIONES.md`
- https://github.com/SebastianSrVentas/deskly-tickets
