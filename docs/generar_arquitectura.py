#!/usr/bin/env python3
"""Genera el diagrama de arquitectura en dos formatos desde una sola fuente.

Salidas:
- docs/arquitectura.drawio  (editable en diagrams.net / draw.io)
- docs/arquitectura.svg     (vista previa para el README)

Uso:
    python docs/generar_arquitectura.py
"""

from __future__ import annotations

import html
import pathlib
from typing import Any

ANCHO = 1200
ALTO = 840

NODOS: list[dict[str, Any]] = [
    {
        "id": "titulo",
        "tipo": "texto",
        "x": 30,
        "y": 18,
        "w": 700,
        "h": 34,
        "texto": "Deskly · arquitectura de contenedores",
        "font_size": 20,
    },
    {
        "id": "red",
        "tipo": "boundary",
        "x": 250,
        "y": 70,
        "w": 910,
        "h": 710,
        "texto": "red interna: deskly_net (bridge) · solo 3000 y 8000 publicados",
    },
    {
        "id": "browser",
        "x": 30,
        "y": 130,
        "w": 170,
        "h": 90,
        "titulo": "Navegador",
        "lineas": ["React 19 (cliente)"],
        "fill": "#e0f2fe",
        "stroke": "#0284c7",
        "font": "#0c4a6e",
    },
    {
        "id": "crm",
        "x": 30,
        "y": 320,
        "w": 170,
        "h": 90,
        "titulo": "Sistema externo",
        "lineas": ["CRM / ERP simulado"],
        "fill": "#f1f5f9",
        "stroke": "#64748b",
        "font": "#334155",
    },
    {
        "id": "frontend",
        "x": 300,
        "y": 130,
        "w": 210,
        "h": 110,
        "titulo": "Frontend",
        "lineas": ["Next.js 15 · App Router", ":3000 · publicado"],
        "fill": "#eef2ff",
        "stroke": "#4f46e5",
        "font": "#312e81",
    },
    {
        "id": "backend",
        "x": 600,
        "y": 120,
        "w": 240,
        "h": 130,
        "titulo": "Backend",
        "lineas": ["FastAPI + Uvicorn", ":8000 · publicado", "Pydantic v2 · FSM"],
        "fill": "#ede9fe",
        "stroke": "#7c3aed",
        "font": "#4c1d95",
    },
    {
        "id": "mongo",
        "x": 940,
        "y": 110,
        "w": 190,
        "h": 110,
        "titulo": "MongoDB 8",
        "lineas": [":27017 · interno", "tickets · auditoría · meta"],
        "fill": "#dcfce7",
        "stroke": "#16a34a",
        "font": "#14532d",
    },
    {
        "id": "redis",
        "x": 900,
        "y": 340,
        "w": 230,
        "h": 150,
        "titulo": "Redis 8.4",
        "lineas": [":6379 · interno", "PUBLISH deskly:eventos", "XADD deskly:cola"],
        "fill": "#fee2e2",
        "stroke": "#dc2626",
        "font": "#7f1d1d",
    },
    {
        "id": "worker",
        "x": 600,
        "y": 510,
        "w": 240,
        "h": 110,
        "titulo": "Worker",
        "lineas": ["consumer group", "XACK · XAUTOCLAIM · DLQ"],
        "fill": "#fef3c7",
        "stroke": "#d97706",
        "font": "#78350f",
    },
    {
        "id": "seguridad",
        "tipo": "note",
        "x": 300,
        "y": 460,
        "w": 250,
        "h": 120,
        "titulo": "Seguridad",
        "lineas": [
            "HMAC-SHA256",
            "timestamp.client_id.body",
            "rate limit 50/s cliente · 100/s IP",
            "request-id + logs JSON",
        ],
    },
    {
        "id": "obs",
        "x": 300,
        "y": 680,
        "w": 820,
        "h": 64,
        "titulo": "Perfil obs (opcional)",
        "lineas": ["Prometheus · Grafana · cAdvisor · exporters"],
        "fill": "#f8fafc",
        "stroke": "#94a3b8",
        "font": "#475569",
        "dashed": True,
    },
]

ARISTAS: list[dict[str, Any]] = [
    {
        "id": "e1",
        "src": "browser",
        "dst": "frontend",
        "label": "HTTP :3000",
        "puntos": [(200, 175), (250, 175), (250, 185), (300, 185)],
        "ambos": True,
        "label_xy": (250, 163),
    },
    {
        "id": "e2",
        "src": "browser",
        "dst": "backend",
        "label": "HTTP :8000 · WS /ws/tickets",
        "puntos": [(200, 150), (230, 150), (230, 108), (680, 108), (680, 120)],
        "ambos": True,
        "dashed": True,
        "label_xy": (445, 98),
    },
    {
        "id": "e3",
        "src": "frontend",
        "dst": "backend",
        "label": "SSR · API_URL_INTERNA",
        "puntos": [(510, 185), (600, 185)],
        "ambos": True,
        "label_xy": (555, 173),
    },
    {
        "id": "e4",
        "src": "crm",
        "dst": "backend",
        "label": "webhook + HMAC",
        "puntos": [(200, 365), (560, 365), (560, 230), (600, 230)],
        "label_xy": (380, 353),
    },
    {
        "id": "e5",
        "src": "backend",
        "dst": "mongo",
        "label": "PyMongo async",
        "puntos": [(840, 175), (940, 165)],
        "ambos": True,
        "label_xy": (890, 153),
    },
    {
        "id": "e6",
        "src": "backend",
        "dst": "redis",
        "label": "PUBLISH + XADD",
        "puntos": [(820, 250), (860, 250), (860, 390), (900, 390)],
        "ambos": True,
        "label_xy": (862, 310),
    },
    {
        "id": "e7",
        "src": "redis",
        "dst": "worker",
        "label": "XREADGROUP / XACK",
        "puntos": [(980, 490), (980, 500), (720, 500), (720, 510)],
        "ambos": True,
        "label_xy": (760, 488),
    },
    {
        "id": "e8",
        "src": "worker",
        "dst": "mongo",
        "label": "auditoría · event_id único",
        "puntos": [(840, 535), (1140, 535), (1140, 220), (1035, 220)],
        "label_xy": (970, 523),
    },
    {
        "id": "e9",
        "src": "backend",
        "dst": "obs",
        "label": "métricas /metrics",
        "puntos": [(620, 250), (560, 250), (560, 680), (620, 680)],
        "dashed": True,
        "label_xy": (500, 655),
    },
]


def escapar(texto: str) -> str:
    return html.escape(texto, quote=False)


def valor_html(nodo: dict[str, Any]) -> str:
    if nodo.get("tipo") in {"texto", "boundary"}:
        return escapar(nodo["texto"])
    lineas = [f"<b>{escapar(nodo['titulo'])}</b>"]
    lineas.extend(escapar(linea) for linea in nodo["lineas"])
    return "<br>".join(lineas)


def estilo_drawio(nodo: dict[str, Any]) -> str:
    tipo = nodo.get("tipo", "caja")
    if tipo == "texto":
        return (
            "text;html=1;align=left;verticalAlign=middle;fillColor=none;"
            "strokeColor=none;fontColor=#0f172a;fontSize=20;fontStyle=1;"
        )
    if tipo == "boundary":
        return (
            "rounded=1;whiteSpace=wrap;html=1;dashed=1;fillColor=none;"
            "strokeColor=#94a3b8;verticalAlign=top;align=right;spacingRight=14;"
            "spacingTop=10;fontColor=#475569;fontSize=12;"
        )
    if tipo == "note":
        return (
            "shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;darkOpacity=0.05;"
            "fillColor=#fef9c3;strokeColor=#ca8a04;align=left;verticalAlign=top;"
            "spacingLeft=14;spacingTop=10;fontColor=#713f12;fontSize=12;"
        )
    dashed = "dashed=1;" if nodo.get("dashed") else ""
    return (
        "rounded=1;whiteSpace=wrap;html=1;arcSize=8;"
        f"fillColor={nodo['fill']};strokeColor={nodo['stroke']};"
        f"fontColor={nodo['font']};fontSize=12;{dashed}"
    )


def generar_drawio() -> str:
    celdas: list[str] = ['<mxCell id="0" />', '<mxCell id="1" parent="0" />']

    for nodo in NODOS:
        valor = html.escape(valor_html(nodo), quote=True)
        estilo = estilo_drawio(nodo)
        celdas.append(
            f'<mxCell id="{nodo["id"]}" value="{valor}" style="{estilo}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{nodo["x"]}" y="{nodo["y"]}" '
            f'width="{nodo["w"]}" height="{nodo["h"]}" as="geometry" />'
            f"</mxCell>"
        )

    for arista in ARISTAS:
        estilo = (
            "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;"
            "strokeColor=#475569;strokeWidth=1.5;endArrow=block;endFill=1;"
            "labelBackgroundColor=#ffffff;fontColor=#334155;fontSize=11;"
        )
        if arista.get("ambos"):
            estilo += "startArrow=block;startFill=1;"
        if arista.get("dashed"):
            estilo += "dashed=1;"

        puntos = arista["puntos"][1:-1]
        array = ""
        if puntos:
            array = (
                '<Array as="points">'
                + "".join(f'<mxPoint x="{x}" y="{y}" />' for x, y in puntos)
                + "</Array>"
            )

        celdas.append(
            f'<mxCell id="{arista["id"]}" value="{html.escape(arista["label"], quote=True)}" '
            f'style="{estilo}" edge="1" parent="1" source="{arista["src"]}" '
            f'target="{arista["dst"]}">'
            f'<mxGeometry relative="1" as="geometry">{array}</mxGeometry>'
            f"</mxCell>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mxfile host="app.diagrams.net" type="device">\n'
        '  <diagram id="arquitectura" name="Arquitectura">\n'
        f'    <mxGraphModel dx="{ANCHO}" dy="{ALTO}" grid="1" gridSize="10" '
        'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" '
        f'pageScale="1" pageWidth="{ANCHO}" pageHeight="{ALTO}" math="0" shadow="0">\n'
        "      <root>\n        "
        + "\n        ".join(celdas)
        + "\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n"
    )


def svg_texto_multilinea(
    x: float,
    y: float,
    titulo: str,
    lineas: list[str],
    ancho: float,
    alto: float,
    color: str,
    centrado: bool = True,
) -> str:
    total = 1 + len(lineas)
    alto_linea = 16
    inicio = y + (alto - total * alto_linea) / 2 + 12
    anchor = "middle" if centrado else "start"
    x_texto = x + ancho / 2 if centrado else x + 14
    partes = [
        f'<text x="{x_texto}" y="{inicio}" text-anchor="{anchor}" '
        f'font-family="Inter, Segoe UI, Arial, sans-serif" font-size="13" '
        f'font-weight="600" fill="{color}">{escapar(titulo)}</text>'
    ]
    for indice, linea in enumerate(lineas, start=1):
        partes.append(
            f'<text x="{x_texto}" y="{inicio + indice * alto_linea}" '
            f'text-anchor="{anchor}" font-family="Inter, Segoe UI, Arial, sans-serif" '
            f'font-size="11" fill="#334155">{escapar(linea)}</text>'
        )
    return "".join(partes)


def generar_svg() -> str:
    partes: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{ALTO}" '
        f'viewBox="0 0 {ANCHO} {ALTO}">',
        "<defs>",
        '<marker id="flecha" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#475569" /></marker>',
        "</defs>",
        f'<rect width="{ANCHO}" height="{ALTO}" fill="#ffffff" />',
    ]

    for nodo in NODOS:
        tipo = nodo.get("tipo", "caja")
        if tipo == "texto":
            partes.append(
                f'<text x="{nodo["x"]}" y="{nodo["y"] + 24}" '
                f'font-family="Inter, Segoe UI, Arial, sans-serif" font-size="20" '
                f'font-weight="700" fill="#0f172a">{escapar(nodo["texto"])}</text>'
            )
            continue

        if tipo == "boundary":
            partes.append(
                f'<rect x="{nodo["x"]}" y="{nodo["y"]}" width="{nodo["w"]}" '
                f'height="{nodo["h"]}" rx="14" fill="none" stroke="#94a3b8" '
                f'stroke-width="1.4" stroke-dasharray="8 6" />'
            )
            partes.append(
                f'<text x="{nodo["x"] + nodo["w"] - 16}" y="{nodo["y"] + 22}" '
                f'text-anchor="end" '
                f'font-family="Inter, Segoe UI, Arial, sans-serif" font-size="12" '
                f'font-weight="500" fill="#475569">{escapar(nodo["texto"])}</text>'
            )
            continue

        if tipo == "note":
            partes.append(
                f'<rect x="{nodo["x"]}" y="{nodo["y"]}" width="{nodo["w"]}" '
                f'height="{nodo["h"]}" rx="8" fill="#fef9c3" stroke="#ca8a04" '
                f'stroke-width="1.4" />'
            )
            partes.append(
                svg_texto_multilinea(
                    nodo["x"],
                    nodo["y"],
                    nodo["titulo"],
                    nodo["lineas"],
                    nodo["w"],
                    nodo["h"],
                    "#713f12",
                    centrado=False,
                )
            )
            continue

        guion = ' stroke-dasharray="6 4"' if nodo.get("dashed") else ""
        partes.append(
            f'<rect x="{nodo["x"]}" y="{nodo["y"]}" width="{nodo["w"]}" '
            f'height="{nodo["h"]}" rx="10" fill="{nodo["fill"]}" '
            f'stroke="{nodo["stroke"]}" stroke-width="1.8"{guion} />'
        )
        partes.append(
            svg_texto_multilinea(
                nodo["x"],
                nodo["y"],
                nodo["titulo"],
                nodo["lineas"],
                nodo["w"],
                nodo["h"],
                nodo["font"],
            )
        )

    for arista in ARISTAS:
        puntos = " ".join(f"{x},{y}" for x, y in arista["puntos"])
        marcadores = 'marker-end="url(#flecha)"'
        if arista.get("ambos"):
            marcadores += ' marker-start="url(#flecha)"'
        guion = ' stroke-dasharray="6 4"' if arista.get("dashed") else ""
        partes.append(
            f'<polyline points="{puntos}" fill="none" stroke="#475569" '
            f'stroke-width="1.5" stroke-linejoin="round" {marcadores}{guion} />'
        )
        lx, ly = arista["label_xy"]
        partes.append(
            f'<text x="{lx}" y="{ly}" text-anchor="middle" '
            f'font-family="Inter, Segoe UI, Arial, sans-serif" font-size="10.5" '
            f'font-weight="500" fill="#334155" stroke="#ffffff" stroke-width="4" '
            f'paint-order="stroke">{escapar(arista["label"])}</text>'
        )

    partes.extend(
        [
            '<line x1="30" y1="762" x2="58" y2="762" stroke="#475569" stroke-width="1.6" '
            'marker-end="url(#flecha)" />',
            '<text x="66" y="766" font-family="Inter, Segoe UI, Arial, sans-serif" '
            'font-size="11" fill="#475569">HTTP / eventos</text>',
            '<line x1="30" y1="790" x2="58" y2="790" stroke="#475569" stroke-width="1.6" '
            'stroke-dasharray="6 4" marker-end="url(#flecha)" />',
            '<text x="66" y="794" font-family="Inter, Segoe UI, Arial, sans-serif" '
            'font-size="11" fill="#475569">opcional / observabilidad</text>',
            '<text x="30" y="824" font-family="Inter, Segoe UI, Arial, sans-serif" '
            'font-size="11" fill="#64748b">Solo 3000 y 8000 se publican al host. '
            'MongoDB y Redis viven en la red interna.</text>',
            "</svg>",
        ]
    )
    return "\n".join(partes) + "\n"


def main() -> None:
    destino = pathlib.Path(__file__).resolve().parent
    (destino / "arquitectura.drawio").write_text(generar_drawio(), encoding="utf-8")
    (destino / "arquitectura.svg").write_text(generar_svg(), encoding="utf-8")
    print("escrito:", destino / "arquitectura.drawio")
    print("escrito:", destino / "arquitectura.svg")


if __name__ == "__main__":
    main()
