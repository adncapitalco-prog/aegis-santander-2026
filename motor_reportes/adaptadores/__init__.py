# -*- coding: utf-8 -*-
"""Adaptadores de dominio del motor de reportes.

Un adaptador traduce los resultados de un dominio al ContratoReporte. Aqui
vive el conocimiento del tema: los nombres, las cifras y las frases.

Niveles disponibles:
    piloto    R-01 estricto: ASD-STE100, cero jerga, una idea por linea.
    tecnico   (Etapa 5a) metodologia, cifras y trazabilidad.
    feynman   (Etapa 5b) explicacion desde cero, con analogias.
"""

from . import piloto, tecnico, feynman  # noqa: F401

__all__ = ["piloto", "tecnico", "feynman"]
