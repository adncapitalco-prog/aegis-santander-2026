# -*- coding: utf-8 -*-
"""Motor de reportes de AEGIS.

Arquitectura en tres capas:

    contrato      QUE se reporta      (agnostico al dominio)
    renderizador  COMO se presenta    (SVG DEGRAU 2 + texto)
    adaptadores   DE DONDE viene      (uno por nivel de lectura)

Regla: el renderizador no conoce el dominio. Si un nombre propio de negocio
aparece en `renderizador.py`, la separacion fallo.
"""

from .contrato import (  # noqa: F401
    Bloque,
    ContratoInvalido,
    ContratoReporte,
    Nodo,
    bloque,
    flujo_simple,
    nodo,
)
from .renderizador import (  # noqa: F401
    escribir,
    renderizar_svg,
    renderizar_texto,
)

__version__ = "1.0.0"

NIVELES = {
    "piloto": "R-01 estricto · ASD-STE100 · cero jerga · SVG DEGRAU 2",
    "tecnico": "Metodologia, trazabilidad y prioridad por puesto",
    "feynman": "Explicacion desde cero con analogias y prioridad",
}
