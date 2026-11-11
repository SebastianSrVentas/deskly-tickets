#!/usr/bin/env python3
"""Genera la firma HMAC y el comando curl para probar el webhook a mano.

Uso:
    python scripts/firmar_webhook.py --secreto "$WEBHOOK_SECRET"
    python scripts/firmar_webhook.py --event-id evt_demo_0001

El body se firma tal cual se envia: sin espacios extra. Si cambias una coma,
la firma deja de valer.
"""

import argparse
import hashlib
import hmac
import json
import time


def main() -> None:
    parser = argparse.ArgumentParser(description="Firma un payload de webhook Deskly")
    parser.add_argument("--secreto", default="cambia-este-secreto-de-desarrollo")
    parser.add_argument("--cliente", default="externo")
    parser.add_argument(
        "--url",
        default="http://localhost:8000/api/webhooks/tickets",
    )
    parser.add_argument("--event-id", default=None)
    parser.add_argument("--titulo", default="Ticket desde el webhook")
    parser.add_argument("--descripcion", default="Creado por un sistema externo simulado")
    parser.add_argument("--prioridad", default="alta", choices=["baja", "media", "alta", "critica"])
    parser.add_argument("--asignado", default="Ana Torres")
    args = parser.parse_args()

    cuerpo: dict[str, str] = {
        "titulo": args.titulo,
        "descripcion": args.descripcion,
        "prioridad": args.prioridad,
        "asignado_a": args.asignado,
    }
    if args.event_id:
        cuerpo["event_id"] = args.event_id

    payload = json.dumps(cuerpo, separators=(",", ":"), ensure_ascii=False)
    timestamp = str(int(time.time()))
    material = f"{timestamp}.{args.cliente}.".encode("utf-8") + payload.encode("utf-8")
    firma = hmac.new(args.secreto.encode("utf-8"), material, hashlib.sha256).hexdigest()

    print(f"X-Client-Id: {args.cliente}")
    print(f"X-Timestamp: {timestamp}")
    print(f"X-Signature: sha256={firma}")
    print()
    print(
        "curl -i -X POST "
        f"'{args.url}' "
        f"-H 'Content-Type: application/json' "
        f"-H 'X-Client-Id: {args.cliente}' "
        f"-H 'X-Timestamp: {timestamp}' "
        f"-H 'X-Signature: sha256={firma}' "
        f"--data '{payload}'"
    )


if __name__ == "__main__":
    main()
