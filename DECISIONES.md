# Decisiones de arquitectura

Formato pedido por el brief: contexto, uso de LLM, salida del modelo y decision
final. El uso de LLM fue intensivo; se documenta lo que se acepto, cambio o
descarto, no una autoria que no corresponde.

---

### [Decision] MongoDB en lugar de PostgreSQL

**Contexto:** El dominio es un ticket con comentarios e historial de estados. La
vista de detalle necesita el ticket completo, y el listado filtra por estado o
prioridad. No hay relaciones entre tickets ni reportes relacionales.

**Uso LLM:** Pedi al agente comparar PostgreSQL y MongoDB para este dominio,
incluyendo el impacto en el detalle SSR y en los filtros.

**Salida del modelo:** Proponia PostgreSQL por integridad referencial y SQL para
los filtros; aceptaba MongoDB si el agregado se leia completo en cada pantalla.

**Mi decision:** MongoDB. El ticket, sus comentarios y su historial se leen en
una sola consulta y se actualizan como un documento; no hay JOINs que justificar
ni transacciones multi-documento. El precio es perder integridad referencial
entre colecciones, que este dominio no necesita. Si el producto creciera a
reportes relacionales o a varias entidades fuertemente acopladas, migraria a
PostgreSQL.

---

### [Decision] Escritura sincrona en MongoDB y eventos asincronos en Redis

**Contexto:** El brief pide Redis y el frontend necesita el `id` del ticket para
navegar al detalle SSR. El test del webhook espera que el ticket exista al
responder.

**Uso LLM:** Pedi un diseno con cola para crear tickets y absorber picos.

**Salida del modelo:** `POST /api/tickets` respondia `202 Accepted` con un
`job_id`; un worker creaba el ticket y publicaba el evento.

**Mi decision:** Descartado. El `202` rompe el contrato: el cliente no tiene
`id`, el detalle SSR no puede consultar el ticket recien creado y el test del
webhook falla. La creacion se escribe de forma sincrona en MongoDB y se responde
`201`; despues se publica en Redis Pub/Sub y se encola en el Stream. La cola
maneja efectos reintentables (auditoria), no la creacion. Si Redis cae, el
ticket ya existe y solo se pierde el evento, que se mide con
`deskly_eventos_fallidos_total`.

---

### [Decision] Dos canales Redis: Pub/Sub para el WebSocket y Stream para trabajo

**Contexto:** Hay dos necesidades distintas: entregar un evento a todos los
clientes conectados y procesar trabajo con reintentos y confirmacion.

**Uso LLM:** Pedi usar Redis Pub/Sub para todo, incluida la cola.

**Salida del modelo:** Un unico canal Pub/Sub; el worker se suscribia y
procesaba los mensajes.

**Mi decision:** Dos canales. Pub/Sub es fan-out puro: si no hay suscriptor, el
mensaje se pierde, y no tiene ack ni reintentos. El Stream con consumer group
tiene `XACK`, `XAUTOCLAIM` y dead letter, pero no es un broadcast eficiente.
Usar Pub/Sub como cola pierde eventos; usar el Stream para el WebSocket obliga a
un consumer group por cliente. `PUBLISH` para los WebSockets, `XADD` para el
worker.

---

### [Decision] Maquina de estados pura y transicion atomica

**Contexto:** El brief exige transiciones explicitas y errores claros. Dos
agentes pueden cambiar el estado del mismo ticket a la vez.

**Uso LLM:** Pedi implementar la maquina de estados y el endpoint de transicion.

**Salida del modelo:** Un `if/elif` dentro del router y un `find` seguido de
`update_one`.

**Mi decision:** La maquina vive en `app/domain/state_machine.py`, sin importar
FastAPI ni MongoDB, para poder probarla sin infraestructura. El `PATCH` no
acepta `estado` (`extra="forbid"`), asi que el unico camino es `/transicion`. La
escritura usa `find_one_and_update({_id, estado: actual}, {$set: {estado:
nuevo}})`; si otra solicitud cambio el estado entre la lectura y la escritura,
el filtro no matchea y se devuelve `409`. Es atomico sin transacciones y se
defiende en la entrevista.

---

### [Decision] Firma HMAC sobre timestamp y client_id, con idempotencia por indice unico

**Contexto:** El webhook debe verificar una firma HMAC-SHA256, rechazar firmas
invalidas con 401 y no crear tickets duplicados si el emisor reintenta.

**Uso LLM:** Pedi el webhook con HMAC del body y un chequeo previo de
`event_id` antes de crear el ticket.

**Salida del modelo:** Firmaba solo el body y hacia `find_one({"event_id": ...})`
antes del `insert_one`.

**Mi decision:** Firme `timestamp.client_id.body`. Firmar solo el body permite
replay; dejar el `client_id` fuera de la firma lo vuelve manipulable y la
trazabilidad miente. La ventana es de 300 s, la comparacion usa
`hmac.compare_digest` y el rate limit se aplica por IP antes del HMAC y por
`client_id` autenticado despues: limitar por un header sin verificar permite
evadir el limite rotando IDs. La idempotencia no se hace con un `find_one`
previo (es una carrera): el ticket se inserta con `event_id` y el indice unique
sparse de MongoDB decide; si hay `DuplicateKeyError`, se devuelve el ticket
original con 200.

---

### [Decision] SSR con URL interna y WebSocket con URL publica

**Contexto:** Next corre en un contenedor y el navegador en el host. El backend
tambien corre en la red interna de Compose.

**Uso LLM:** Pedi conectar el frontend al backend usando una sola variable de
entorno.

**Salida del modelo:** `NEXT_PUBLIC_API_URL=http://localhost:8000` para los
Server Components y para el navegador.

**Mi decision:** Dos URLs. Los Server Components usan
`API_URL_INTERNA=http://backend:8000`; dentro del contenedor de Next,
`localhost` es Next, no el backend, y el SSR fallaria. El navegador usa
`NEXT_PUBLIC_API_URL=http://localhost:8000`. El hook `useTicketStream` deriva
`ws://` de la URL publica o usa `NEXT_PUBLIC_WS_URL` si el WebSocket vive en
otro host. Para actualizar la UI sin recargar, `router.refresh()` revalida el
Server Component; un debounce de 300 ms evita una revalidacion por cada evento
de una rafaga.

---

### [Decision] Python 3.14 si, t-strings no

**Contexto:** El brief no fija version de Python. El usuario propuso 3.14 para
usar t-strings en los logs y el HTML.

**Uso LLM:** Pedi verificar que el stack tuviera wheels para 3.14 y evaluar
t-strings en el dominio.

**Salida del modelo:** Verifico wheels `cp314` para Pydantic, PyMongo, Uvicorn y
`uvloop`; propuso t-strings en el logging.

**Mi decision:** 3.14 si, t-strings no. MongoDB devuelve dicts, Next renderiza
el HTML, HMAC firma bytes y el logger espera un `str`; los t-strings no aportan
y serian codigo decorativo. Se usan las funciones modernas que si aplican:
`StrEnum`, `Annotated`, `Field` y `ConfigDict(extra="forbid")`.

---

### [Decision] Tailwind 4 en lugar de Bootstrap

**Contexto:** Habia que construir un dashboard denso y un detalle con estados de
UI diferenciados, sin añadir otro sistema de estilos al scaffold de Next.

**Uso LLM:** Pedi comparar Bootstrap y Tailwind, y luego tres mockups con
posturas visuales distintas.

**Salida del modelo:** Bootstrap acelera los componentes; Tailwind da control y
evita peleas de especificidad. Los mockups fueron utilitarian dense, calm
editorial y command center.

**Mi decision:** Tailwind 4, que ya venia con `create-next-app`. Se definieron
tokens en `globals.css` y componentes propios (`.card`, `.badge`, `.btn`) en
lugar de dos resets y dos sistemas de clases. Del ejercicio de mockups se tomo
la densidad de la tabla del primero y el header oscuro del tercero.

---

### [Decision] Worker con ack, reintentos y dead letter queue

**Contexto:** La publicacion de eventos no debe bloquear la respuesta HTTP, pero
tampoco debe perder trabajo si el proceso que lo consume falla.

**Uso LLM:** Pedi un worker que auditara los eventos.

**Salida del modelo:** Un bucle que leia el Stream y llamara al manejador, sin
consumer group.

**Mi decision:** Consumer group `deskly-workers`, `XACK` tras procesar,
`XAUTOCLAIM` a los 60 s, tres intentos y `deskly:cola:muertos`. La auditoria en
Mongo tiene indice unique por `event_id`, asi que un reintento no duplica. El
cliente del worker usa `socket_timeout=10` porque `XREADGROUP` bloquea 5 s; un
timeout menor corta la lectura y el worker entra en bucle. Es mas de lo que el
brief pide, pero demuestra el patron completo y cuesta un solo contenedor.
