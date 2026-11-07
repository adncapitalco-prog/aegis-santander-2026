# -*- coding: utf-8 -*-
"""
CAPA 2 · RENDERIZADOR
=====================

Convierte un ContratoReporte en las dos piezas de R-01:
  - un diagrama SVG con estilo DEGRAU 2
  - un texto plano listo para enviar

REGLA DE ORO
------------
Aqui no aparece ningun nombre propio de dominio. Ni municipios, ni puestos, ni
partidos, ni valvulas, ni activos. Si un nombre concreto vive en este archivo,
la separacion de capas fallo.

El renderizador solo sabe de:
  - roles semantico ('entrada', 'perdida', 'objetivo', 'accion'...)
  - cantidades de nodos
  - lineas de texto que alguien mas redacto

Que decide el renderizador
--------------------------
Colores por rol, posiciones, tipografia, margenes y el orden de los bloques.
Eso es presentacion y le corresponde a esta capa.
"""

from __future__ import annotations

import os
from typing import Dict, List, Sequence

from .contrato import ContratoReporte

# =============================================================================
# PALETA DEGRAU 2
# =============================================================================
FONDO = "#0E1117"
TEXTO = "#F2F5F7"
TENUE = "#9AA5B1"
NODO = "#16202B"
BORDE = "#2A3A4A"

# Color por rol semantico. El contrato habla de roles; el renderizador decide
# como se ven. Un dominio nuevo no necesita tocar esta tabla.
COLOR_ROL = {
    "entrada": "#457B9D",
    "proceso": "#457B9D",
    "perdida": "#D32F2F",
    "objetivo": "#E8A33D",
    "accion": "#1B7A3D",
    "neutro": "#2A3A4A",
}

FUENTE = "Inter,Segoe UI,sans-serif"

# Geometria del lienzo
ANCHO = 980
ALTO_BASE = 560
MARGEN = 40
GAP = 80
ALTO_NODO = 96
Y_FILAS = (100, 250, 405)

# Presentacion de los objetivos dentro del nodo de accion.
MAX_OBJETIVOS_VISIBLES = 5
SEPARADOR_OBJETIVOS = " \u00b7 "          # punto medio
COLOR_OBJETIVOS = "#F2F5F7"
TAM_OBJETIVOS = 12
ALTO_LINEA_OBJETIVOS = 18


# =============================================================================
# DISPOSICION
# =============================================================================
def _filas(n: int) -> List[int]:
    """Reparte n nodos en filas. La ultima fila la ocupa la accion.

    Regla: hasta 3 por fila. Si hay accion, va sola al final y a todo el ancho.
    """
    if n <= 3:
        return [n]
    if n <= 6:
        return [3, n - 3]
    return [3, 3, n - 6]


def _anchos(fila: int, total: int) -> List[int]:
    """Reparte el ancho disponible en partes iguales, salvo la accion."""
    if fila == 1:
        return [ANCHO - 2 * MARGEN]
    util = ANCHO - 2 * MARGEN - GAP * (fila - 1)
    base = util // fila
    anchos = [base] * fila
    anchos[-1] = util - base * (fila - 1)  # absorbe el resto del redondeo
    return anchos


def calcular_posiciones(n: int, alto_accion: int = ALTO_NODO) -> List[Dict[str, int]]:
    """Devuelve x, y, ancho y alto de cada nodo, sin conocer su contenido.

    `alto_accion` permite que el nodo de accion crezca cuando lleva objetivos
    o mas lineas de las habituales. El texto nunca se recorta: el nodo se
    adapta.
    """
    reparto = _filas(n)
    posiciones: List[Dict[str, int]] = []
    indice = 0
    for numero_fila, cantidad in enumerate(reparto):
        y = Y_FILAS[min(numero_fila, len(Y_FILAS) - 1)]
        anchos = _anchos(cantidad, n)
        x = MARGEN
        es_ultima = numero_fila == len(reparto) - 1
        alto = alto_accion if es_ultima and cantidad == 1 else ALTO_NODO
        for ancho in anchos:
            posiciones.append({"x": x, "y": y, "w": ancho, "h": alto, "fila": numero_fila})
            x += ancho + GAP
            indice += 1
    return posiciones[:n]


# =============================================================================
# SVG
# =============================================================================
def _escapar(texto: str) -> str:
    return (str(texto).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def linea_objetivos(objetivos: Sequence[str]) -> str:
    """Junta los objetivos en una linea legible.

    Regla: se muestran los primeros MAX_OBJETIVOS_VISIBLES. Si hay mas, se
    anade "+N mas". El renderizador no sabe que representan: solo los separa.
    """
    limpios = [str(o).strip() for o in (objetivos or []) if str(o).strip()]
    if not limpios:
        return ""
    visibles = limpios[:MAX_OBJETIVOS_VISIBLES]
    texto = SEPARADOR_OBJETIVOS.join(visibles)
    resto = len(limpios) - len(visibles)
    if resto > 0:
        texto += "  +%d mas" % resto
    return texto


def _nodo_svg(pos: Dict[str, int], nodo, color: str,
              objetivos: str = "") -> str:
    x, y, w, h = pos["x"], pos["y"], pos["w"], pos["h"]
    partes = [
        '<rect x="%d" y="%d" width="%d" height="%d" rx="10" fill="%s" '
        'stroke="%s" stroke-width="2"/>' % (x, y, w, h, NODO, color)
    ]
    detalle = nodo.detalle
    y_titulo = y + (34 if detalle else h // 2 + 7)
    partes.append(
        '<text x="%d" y="%d" text-anchor="middle" fill="%s" font-family="%s" '
        'font-size="19" font-weight="700">%s</text>'
        % (x + w // 2, y_titulo, color if nodo.rol in ("perdida", "objetivo") else TEXTO,
           FUENTE, _escapar(nodo.titulo))
    )
    desplazamiento = 0
    for i, linea in enumerate(detalle):
        partes.append(
            '<text x="%d" y="%d" text-anchor="middle" fill="%s" font-family="%s" '
            'font-size="13">%s</text>'
            % (x + w // 2, y + 56 + i * 17, TENUE, FUENTE, _escapar(linea))
        )
        desplazamiento = 56 + i * 17
    if objetivos:
        partes.append(
            '<text x="%d" y="%d" text-anchor="middle" fill="%s" font-family="%s" '
            'font-size="%d" font-weight="600">%s</text>'
            % (x + w // 2, y + desplazamiento + ALTO_LINEA_OBJETIVOS,
               COLOR_OBJETIVOS, FUENTE, TAM_OBJETIVOS, _escapar(objetivos))
        )
    return "".join(partes)


def _flecha_svg(x1: int, y1: int, x2: int, y2: int, color: str) -> str:
    return ('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2.5" '
            'marker-end="url(#punta)"/>' % (x1, y1, x2, y2, color))


def _conectar(pos_a: Dict[str, int], pos_b: Dict[str, int], color: str) -> str:
    """Flecha entre dos nodos: horizontal si comparten fila, vertical si no."""
    if pos_a["fila"] == pos_b["fila"]:
        x1 = pos_a["x"] + pos_a["w"]
        y1 = pos_a["y"] + pos_a["h"] // 2
        x2 = pos_b["x"] - 2
        return _flecha_svg(x1, y1, x2, y1, color)
    x1 = pos_a["x"] + pos_a["w"] // 2
    y1 = pos_a["y"] + pos_a["h"]
    y2 = pos_b["y"] - 2
    return _flecha_svg(x1, y1, x1, y2, color)


def _texto_svg(x: int, y: int, contenido: str, tam: int, color: str,
               ancla: str = "middle", peso: str = "400") -> str:
    return ('<text x="%d" y="%d" text-anchor="%s" fill="%s" font-family="%s" '
            'font-size="%d" font-weight="%s">%s</text>'
            % (x, y, ancla, color, FUENTE, tam, peso, _escapar(contenido)))


def renderizar_svg(contrato: ContratoReporte) -> str:
    """Produce el SVG completo."""
    n = len(contrato.nodos)

    # Altura del nodo de accion: crece si lleva objetivos o detalle largo.
    texto_objetivos = linea_objetivos(getattr(contrato, "puestos_objetivo", []))
    nodo_accion = next((x for x in contrato.nodos if x.rol == "accion"), None)
    lineas_extra = 0
    if nodo_accion is not None:
        lineas_extra = len(nodo_accion.detalle) + (1 if texto_objetivos else 0)
    alto_accion = max(ALTO_NODO, 56 + lineas_extra * ALTO_LINEA_OBJETIVOS + 20)

    posiciones = calcular_posiciones(n, alto_accion)
    alto = ALTO_BASE if n < 7 else ALTO_BASE + (alto_accion - ALTO_NODO)

    piezas = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="100%%" '
        'style="max-width:%dpx;background:%s;border-radius:14px;display:block">'
        % (ANCHO, alto, ANCHO, FONDO),
        '<defs><marker id="punta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="%s"/></marker></defs>' % BORDE,
        '<rect width="%d" height="%d" fill="%s"/>' % (ANCHO, alto, FONDO),
        _texto_svg(MARGEN, 46, contrato.titulo, 21, TEXTO, ancla="start", peso="700"),
        _texto_svg(MARGEN, 70, contrato.subtitulo, 13, TENUE, ancla="start"),
    ]

    for origen, destino in contrato.conexiones:
        color = COLOR_ROL.get(contrato.nodos[destino].rol, BORDE)
        piezas.append(_conectar(posiciones[origen], posiciones[destino], color))

    for nodo, pos in zip(contrato.nodos, posiciones):
        objetivos = texto_objetivos if nodo.rol == "accion" else ""
        piezas.append(_nodo_svg(pos, nodo, COLOR_ROL.get(nodo.rol, BORDE), objetivos))

    piezas.append('</svg>')
    return "".join(piezas)


# =============================================================================
# TEXTO
# =============================================================================
def renderizar_texto(contrato: ContratoReporte) -> str:
    """Produce el texto plano: titulo, bloques, accion, pie.

    El renderizador no redacta: ordena y separa. Las frases vienen del
    adaptador de dominio, que es quien conoce el tema.
    """
    lineas: List[str] = [contrato.titulo, ""]
    for bloque in contrato.bloques:
        if bloque.rotulo:
            lineas.append(bloque.rotulo)
            lineas.append("")
        for linea in bloque.lineas:
            lineas.append(linea)
        lineas.append("")
    # El texto no repite la accion como linea suelta: el adaptador la incluye
    # dentro de sus bloques. Repetirla aqui duplicaria el mensaje y romperia
    # la compatibilidad con los reportes ya emitidos.
    if contrato.pie:
        lineas.append("")
        lineas.append(contrato.pie)
    # colapsa triples saltos
    salida: List[str] = []
    for linea in lineas:
        if linea == "" and salida and salida[-1] == "":
            continue
        salida.append(linea)
    return "\n".join(salida).strip() + "\n"


# =============================================================================
# ESCRITURA
# =============================================================================
def escribir(contrato: ContratoReporte, carpeta: str,
             nombre_svg: str = "diagrama_piloto.svg",
             nombre_texto: str = "texto_piloto.txt") -> Dict[str, str]:
    """Escribe las dos piezas a disco. Devuelve las rutas."""
    os.makedirs(carpeta, exist_ok=True)
    ruta_svg = os.path.join(carpeta, nombre_svg)
    ruta_txt = os.path.join(carpeta, nombre_texto)
    with open(ruta_svg, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(renderizar_svg(contrato))
    with open(ruta_txt, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(renderizar_texto(contrato))
    return {"svg": ruta_svg, "texto": ruta_txt}
