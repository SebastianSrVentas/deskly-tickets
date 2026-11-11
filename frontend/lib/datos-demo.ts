import type { Ticket } from "@/types/ticket";

/*
 * Datos de ejemplo para desarrollar la interfaz antes de que existan los
 * endpoints REST. Cuando el backend este listo, `app/page.tsx` cambia
 * `TICKETS_DEMO` por `listarTickets()` de `lib/api.ts`.
 */
export const TICKETS_DEMO: Ticket[] = [
  {
    id: "T-1042",
    titulo: "No puedo acceder a mi cuenta desde el cambio de contrasena",
    descripcion:
      "Desde ayer intento entrar y el sistema me devuelve al login sin mostrar ningun mensaje de error. Ya limpie cache y cookies en Chrome y Safari.",
    prioridad: "critica",
    estado: "abierto",
    asignado_a: "Maria Gonzalez",
    creado_en: "2026-11-11T17:48:00Z",
    actualizado_en: "2026-11-11T17:48:00Z",
    comentarios: [
      {
        id: "c-1",
        autor: "Maria Gonzalez",
        texto:
          "El usuario reporta que despues de cambiar la contrasena, cualquier intento de login lo regresa a la pantalla inicial sin mensaje.",
        creado_en: "2026-11-11T17:50:00Z",
      },
      {
        id: "c-2",
        autor: "Carlos Ruiz",
        texto:
          "Revise los logs del servicio de sesiones: hay un 401 repetido con el mismo token. Sospecho que el refresh token no se rota al cambiar la contrasena.",
        creado_en: "2026-11-11T17:54:00Z",
      },
    ],
  },
  {
    id: "T-1041",
    titulo: "Error 500 al generar la factura mensual",
    descripcion:
      "El boton de descarga de la factura devuelve error 500 desde la actualizacion del viernes. Afecta a todos los clientes del plan Pro.",
    prioridad: "alta",
    estado: "en_progreso",
    asignado_a: "Carlos Ruiz",
    creado_en: "2026-11-11T17:26:00Z",
    actualizado_en: "2026-11-11T17:40:00Z",
    comentarios: [
      {
        id: "c-3",
        autor: "Carlos Ruiz",
        texto:
          "Reproducido en staging. El stack apunta al servicio de plantillas, que devuelve un timeout al renderizar la factura.",
        creado_en: "2026-11-11T17:35:00Z",
      },
    ],
  },
  {
    id: "T-1040",
    titulo: "Solicitud de reembolso duplicado en el ultimo cobro",
    descripcion:
      "Se cobro dos veces la suscripcion de octubre. El cliente pide la devolucion del segundo cargo y la correccion de la factura.",
    prioridad: "media",
    estado: "abierto",
    asignado_a: "Ana Torres",
    creado_en: "2026-11-11T17:00:00Z",
    actualizado_en: "2026-11-11T17:00:00Z",
    comentarios: [],
  },
  {
    id: "T-1039",
    titulo: "La integracion con Slack dejo de enviar notificaciones",
    descripcion:
      "Los mensajes llegan al canal pero sin el enlace al ticket. Ocurre desde que se rotaron las credenciales del workspace.",
    prioridad: "alta",
    estado: "resuelto",
    asignado_a: "Maria Gonzalez",
    creado_en: "2026-11-11T16:10:00Z",
    actualizado_en: "2026-11-11T16:55:00Z",
    comentarios: [
      {
        id: "c-4",
        autor: "Maria Gonzalez",
        texto:
          "El token nuevo no tenia el scope de enlaces. Se actualizo el permiso y se reenvio la prueba.",
        creado_en: "2026-11-11T16:50:00Z",
      },
    ],
  },
  {
    id: "T-1038",
    titulo: "Cambio de plan a Enterprise con prorrateo",
    descripcion:
      "El cliente quiere subir de plan a mitad de mes y necesita saber el monto prorrateado antes de confirmar.",
    prioridad: "media",
    estado: "en_progreso",
    asignado_a: "Carlos Ruiz",
    creado_en: "2026-11-11T15:20:00Z",
    actualizado_en: "2026-11-11T15:45:00Z",
    comentarios: [],
  },
  {
    id: "T-1037",
    titulo: "Exportar historial de tickets a CSV",
    descripcion:
      "Solicitud de exportacion masiva para auditoria interna. Se valido con el cliente y se cerro el requerimiento.",
    prioridad: "baja",
    estado: "cerrado",
    asignado_a: "Ana Torres",
    creado_en: "2026-11-10T18:30:00Z",
    actualizado_en: "2026-11-10T19:10:00Z",
    comentarios: [],
  },
  {
    id: "T-1036",
    titulo: "El buscador no encuentra tickets con acentos",
    descripcion:
      "Al buscar palabras con tilde el resultado sale vacio. Sin tilde funciona correctamente.",
    prioridad: "media",
    estado: "abierto",
    asignado_a: null,
    creado_en: "2026-11-11T14:05:00Z",
    actualizado_en: "2026-11-11T14:05:00Z",
    comentarios: [],
  },
  {
    id: "T-1035",
    titulo: "Webhook de pagos devuelve 401 de forma intermitente",
    descripcion:
      "Uno de cada diez eventos del proveedor de pagos llega con firma invalida. El proveedor dice que su reloj esta sincronizado.",
    prioridad: "critica",
    estado: "en_progreso",
    asignado_a: "Maria Gonzalez",
    creado_en: "2026-11-11T12:40:00Z",
    actualizado_en: "2026-11-11T13:15:00Z",
    comentarios: [],
  },
  {
    id: "T-1034",
    titulo: "Agregar segundo factor de autenticacion para agentes",
    descripcion:
      "Requerimiento de seguridad: los agentes con permisos de administracion deben usar TOTP.",
    prioridad: "alta",
    estado: "abierto",
    asignado_a: "Carlos Ruiz",
    creado_en: "2026-11-11T11:10:00Z",
    actualizado_en: "2026-11-11T11:10:00Z",
    comentarios: [],
  },
  {
    id: "T-1033",
    titulo: "El tablero tarda mas de cinco segundos en cargar",
    descripcion:
      "Con mas de mil tickets el listado tarda en responder. Se requiere revisar los indices de la base.",
    prioridad: "alta",
    estado: "resuelto",
    asignado_a: "Ana Torres",
    creado_en: "2026-11-10T16:00:00Z",
    actualizado_en: "2026-11-10T17:30:00Z",
    comentarios: [],
  },
  {
    id: "T-1032",
    titulo: "Solicitud de eliminacion de datos de una cuenta",
    descripcion:
      "El cliente ejerce su derecho de eliminacion. Se requiere confirmar el proceso y el plazo de respuesta.",
    prioridad: "media",
    estado: "cerrado",
    asignado_a: "Maria Gonzalez",
    creado_en: "2026-11-09T15:20:00Z",
    actualizado_en: "2026-11-10T09:00:00Z",
    comentarios: [],
  },
  {
    id: "T-1031",
    titulo: "Corregir texto de la pantalla de bienvenida",
    descripcion:
      "El parrafo de bienvenida menciona un plan que ya no existe. Es un cambio de copy menor.",
    prioridad: "baja",
    estado: "abierto",
    asignado_a: null,
    creado_en: "2026-11-09T10:00:00Z",
    actualizado_en: "2026-11-09T10:00:00Z",
    comentarios: [],
  },
];
