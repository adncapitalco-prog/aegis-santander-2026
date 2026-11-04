# -*- coding: utf-8 -*-
"""
CAPA 1 · CONTRATO DE REPORTE
============================

Define QUE se reporta, sin saber de que dominio viene ni como se dibuja.

Que vive aqui
-------------
Las estructuras de datos que atraviesan el motor: un reporte es un titulo,
un flujo de nodos con flechas, una accion principal y una serie de bloques de
texto. Nada mas.

Que NO vive aqui
----------------
- Nombres de municipios, puestos, partidos, valvulas o activos.
- Formulas de ningun dominio.
- Decisiones de color, tamano o tipografia.

Un contrato valido se puede llenar con datos electorales, financieros o
industriales sin cambiar una linea de este archivo.

LIMITES DUROS
-------------
DEGRAU 2 admite como maximo 7 nodos. El contrato lo hace cumplir aqui, antes
de que el renderizador tenga que defenderse.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

VERSION = "1.0.0"

MAX_NODOS = 7
MAX_LINEAS_DETALLE = 3
MAX_ACCIONES = 5

# Rol semantico del nodo. El renderizador traduce esto a color, nunca al reves.
ROLES = ("entrada", "proceso", "perdida", "objetivo", "accion", "neutro")


class ContratoInvalido(ValueError):
    """El contrato no cumple las reglas de DEGRAU 2."""


@dataclass
class Nodo:
    """Un bloque del diagrama.

    titulo   : la cifra o la idea, en dos o tres palabras.
    detalle  : lineas de apoyo. Maximo tres, cortas.
    rol      : 'entrada' | 'proceso' | 'perdida' | 'objetivo' | 'accion' | 'neutro'
    """

    titulo: str
    detalle: List[str] = field(default_factory=list)
    rol: str = "neutro"

    def __post_init__(self) -> None:
        if not self.titulo or not self.titulo.strip():
            raise ContratoInvalido("Un nodo no puede tener titulo vacio.")
        if self.rol not in ROLES:
            raise ContratoInvalido(
                "Rol desconocido: '%s'. Validos: %s" % (self.rol, ", ".join(ROLES))
            )
        if len(self.detalle) > MAX_LINEAS_DETALLE:
            raise ContratoInvalido(
                "El nodo '%s' tiene %d lineas de detalle; el maximo es %d."
                % (self.titulo, len(self.detalle), MAX_LINEAS_DETALLE)
            )


@dataclass
class Bloque:
    """Un bloque del texto: un rotulo y sus lineas."""

    rotulo: str
    lineas: List[str] = field(default_factory=list)


@dataclass
class ContratoReporte:
    """Lo que un dominio entrega al motor para que exista un reporte."""

    titulo: str
    subtitulo: str
    nodos: List[Nodo]
    conexiones: List[Tuple[int, int]]
    accion: str
    # Objetivos concretos sobre los que actuar. El renderizador los dibuja en
    # el nodo de accion, pero no sabe que son: podrian ser puestos de
    # votacion, valvulas, activos o cuentas. Es el dominio quien los nombra.
    puestos_objetivo: List[str] = field(default_factory=list)
    bloques: List[Bloque] = field(default_factory=list)
    pie: str = ""
    metadatos: Dict[str, str] = field(default_factory=dict)
    # Datos de soporte que solo algunos niveles usan: formula aplicada,
    # descomposicion, hashes de fuente, controles de QA y limites declarados.
    # El dominio lo llena; los adaptadores lo formatean sin interpretarlo.
    anexos: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    def __post_init__(self) -> None:
        if not self.titulo.strip():
            raise ContratoInvalido("El reporte necesita un titulo.")
        if not self.nodos:
            raise ContratoInvalido("El reporte necesita al menos un nodo.")
        if len(self.nodos) > MAX_NODOS:
            raise ContratoInvalido(
                "DEGRAU 2 admite %d nodos como maximo; se recibieron %d."
                % (MAX_NODOS, len(self.nodos))
            )
        for origen, destino in self.conexiones:
            for indice in (origen, destino):
                if not (0 <= indice < len(self.nodos)):
                    raise ContratoInvalido(
                        "Conexion fuera de rango: %d (hay %d nodos)."
                        % (indice, len(self.nodos))
                    )
        self.puestos_objetivo = [p.strip() for p in self.puestos_objetivo if p and p.strip()]
        if not self.accion.strip():
            raise ContratoInvalido(
                "El reporte necesita una accion. Un reporte sin accion no es un "
                "reporte: es una descripcion."
            )

    # ------------------------------------------------------------------
    def validar_texto(self, max_palabras: int = 20) -> List[str]:
        """Comprueba la regla R-01.2 sobre los bloques de texto.

        Devuelve la lista de lineas que exceden el limite. Vacia = cumple.
        """
        excesos = []
        for bloque in self.bloques:
            for linea in bloque.lineas:
                palabras = len(linea.split())
                if palabras > max_palabras:
                    excesos.append(
                        "%d palabras (%s): %s" % (palabras, bloque.rotulo, linea)
                    )
        return excesos

    def resumen(self) -> Dict[str, object]:
        """Vista compacta para probar y para registrar en bitacora."""
        return {
            "titulo": self.titulo,
            "nodos": len(self.nodos),
            "conexiones": len(self.conexiones),
            "bloques": len(self.bloques),
            "lineas": sum(len(b.lineas) for b in self.bloques),
            "roles": [n.rol for n in self.nodos],
            "puestos_objetivo": len(self.puestos_objetivo),
        }


# =============================================================================
# AYUDANTES DE CONSTRUCCION
# =============================================================================
def nodo(titulo: str, detalle: Optional[Sequence[str]] = None, rol: str = "neutro") -> Nodo:
    return Nodo(titulo.strip(), [d.strip() for d in (detalle or [])], rol)


def bloque(rotulo: str, lineas: Sequence[str]) -> Bloque:
    return Bloque(rotulo, [l.strip() for l in lineas if l and l.strip()])


def flujo_simple(n: int) -> List[Tuple[int, int]]:
    """Conecta los nodos en cadena: 0->1, 1->2, ..."""
    return [(i, i + 1) for i in range(n - 1)]
