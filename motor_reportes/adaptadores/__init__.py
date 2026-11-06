# -*- coding: utf-8 -*-
"""Adaptadores de dominio del motor de reportes.

Un adaptador traduce los resultados de un dominio al ContratoReporte. Aqui
vive el conocimiento del tema: los nombres, las cifras y las frases.

Niveles disponibles:
    piloto    R-01 estricto: ASD-STE100, cero jerga, una idea por linea.
              Devuelve un ContratoReporte; el renderizador lo dibuja.
    tecnico   Metodologia, formula, hashes de fuente, control de calidad,
              limites declarados y tabla de prioridad por puesto.
              Devuelve markdown.
    feynman   Explicacion desde cero, con analogias cotidianas y la
              prioridad de cada puesto narrada sin jerga.
              Devuelve markdown.

Los tres leen el MISMO ContratoReporte. Ninguno extrae datos ni conoce el
dominio: eso vive en `datos_electorales.py`, en la capa de datos.
"""

from . import feynman, piloto, tecnico  # noqa: F401

__all__ = ["piloto", "tecnico", "feynman"]

NIVELES = {
    "piloto": "ContratoReporte · renderizador SVG DEGRAU 2 + texto STE",
    "tecnico": "Markdown · metodologia, trazabilidad y prioridad",
    "feynman": "Markdown · narrativa y prioridad sin jerga",
}
