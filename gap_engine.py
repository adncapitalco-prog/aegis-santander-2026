#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GAP ENGINE · AEGIS
==================

Motor genérico de brecha recuperable. Calcula cuánto valor se está perdiendo
entre lo que un sistema podría rendir y lo que rinde, descontando lo que no
es alcanzable y lo que cuesta alcanzarlo.

FORMULA
-------
    BRECHA = (POTENCIAL - REALIZADO) x ACCESIBILIDAD - COSTO

Los tres parámetros tienen el mismo significado en cualquier dominio:

    POTENCIAL     el techo: lo que se podría capturar si todo funcionara
    REALIZADO     lo que efectivamente se capturó
    ACCESIBILIDAD fracción de la brecha que está realmente disponible (0..1)
    COSTO         esfuerzo de capturarla, en la unidad del dominio

EL PROBLEMA DE LA ACCESIBILIDAD
-------------------------------
Si ACCESIBILIDAD se asume en 1, la fórmula devuelve el techo y el resultado
es siempre el mismo número optimista. Eso no es una medición: es una
esperanza.

Por eso el motor trabaja por COMPONENTES. La brecha total se descompone en
partes, y cada parte declara si su accesibilidad está medida o no:

    - Si TODAS están medidas -> devuelve un número único con confianza.
    - Si ALGUNA no lo está  -> devuelve un rango {piso, techo, incertidumbre}.

Un rango honesto vale más que un número inventado. Esa es la lección que el
sistema electoral dejó: 353.282 votos de Santander no tienen dueño conocido,
y por eso el índice de oportunidad se publicó como techo, nunca como certeza.

USO
---
    from gap_engine import GapEngine, Componente

    resultado = GapEngine.estimar(
        potencial=273156,
        realizado=249586,
        componentes=[
            Componente("blancos", 10374, accesibilidad=0.371, fuente="conversion observada"),
            Componente("nulos",    5022, accesibilidad=0.0,   fuente="no convirtieron"),
            Componente("caida",    8174, accesibilidad=None,  fuente="sin contrafactual"),
        ],
    )
    print(resultado["piso"], resultado["techo"], resultado["incertidumbre"])
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

VERSION = "1.0.0"

# Umbrales de incertidumbre sobre la amplitud del rango, relativa al techo.
UMBRAL_BAJA = 0.10
UMBRAL_MEDIA = 0.35


@dataclass
class Componente:
    """Una parte de la brecha, con su propia accesibilidad.

    accesibilidad:
        float  -> medida. 0 = no se puede capturar nada, 1 = se captura todo.
        None   -> desconocida. El motor devuelve rango, no un número.
    """

    nombre: str
    monto: float
    accesibilidad: Optional[float] = None
    fuente: str = ""
    costo: float = 0.0

    def __post_init__(self) -> None:
        if self.monto < 0:
            raise ValueError(
                "El monto de '%s' es negativo (%s). La brecha no puede ser negativa: "
                "usa componentes separados para capturas y pérdidas." % (self.nombre, self.monto)
            )
        if self.accesibilidad is not None and not (0.0 <= self.accesibilidad <= 1.0):
            raise ValueError(
                "Accesibilidad fuera de rango en '%s': %s. Debe estar entre 0 y 1."
                % (self.nombre, self.accesibilidad)
            )

    @property
    def medida(self) -> bool:
        return self.accesibilidad is not None

    def aporte_piso(self) -> float:
        if self.accesibilidad is None:
            return 0.0
        return max(0.0, self.monto * self.accesibilidad - self.costo)

    def aporte_techo(self) -> float:
        return max(0.0, self.monto * 1.0 - self.costo)


@dataclass
class Resultado:
    """Lo que devuelve el motor. Siempre con la estructura completa."""

    brecha: Optional[float]
    piso: float
    techo: float
    incertidumbre: str
    confianza: str
    componentes: List[Dict] = field(default_factory=list)
    advertencias: List[str] = field(default_factory=list)

    def como_dict(self) -> Dict:
        return {
            "brecha": self.brecha,
            "piso": self.piso,
            "techo": self.techo,
            "incertidumbre": self.incertidumbre,
            "confianza": self.confianza,
            "componentes": self.componentes,
            "advertencias": self.advertencias,
        }


class GapEngine:
    """Calcula la brecha recuperable de cualquier dominio."""

    # ------------------------------------------------------------------
    # NUCLEO
    # ------------------------------------------------------------------
    @staticmethod
    def estimar(
        potencial: float,
        realizado: float,
        componentes: Optional[Sequence[Componente]] = None,
        accesibilidad: Optional[float] = None,
        costo: float = 0.0,
        tolerancia: float = 0.01,
    ) -> Resultado:
        """Calcula la brecha.

        Dos caminos:

          A) Con COMPONENTES: cada parte aporta su propio piso y techo.
             Es el camino recomendado y el que produce rangos honestos.

          B) Sin componentes: se aplica la formula directa sobre el total.
             Si accesibilidad es None, el rango es [0, brecha_total].

        'tolerancia' es el margen con el que se acepta que la suma de
        componentes cuadre con (potencial - realizado), por defecto 1 %.
        """
        advertencias: List[str] = []

        if potencial < realizado:
            advertencias.append(
                "POTENCIAL (%s) es menor que REALIZADO (%s). La brecha seria "
                "negativa; se trata como cero." % (potencial, realizado)
            )
        brecha_total = max(0.0, potencial - realizado)

        # --- Camino B: formula directa ---
        if not componentes:
            if accesibilidad is None:
                piso = max(0.0, 0.0 - costo)
                techo = max(0.0, brecha_total - costo)
                inc = GapEngine._incertidumbre(techo - piso, techo)
                return Resultado(
                    brecha=None, piso=piso, techo=techo, incertidumbre=inc,
                    confianza="Baja", componentes=[],
                    advertencias=advertencias + [
                        "Sin componentes y sin accesibilidad medida: el rango va "
                        "de cero al techo. Se declara como incertidumbre alta."
                    ],
                )
            valor = max(0.0, brecha_total * accesibilidad - costo)
            return Resultado(
                brecha=valor, piso=valor, techo=valor,
                incertidumbre="Nula", confianza="Alta", componentes=[],
                advertencias=advertencias,
            )

        # --- Camino A: por componentes ---
        suma_montos = sum(c.monto for c in componentes)
        if brecha_total > 0 and abs(suma_montos - brecha_total) > tolerancia * brecha_total:
            advertencias.append(
                "La suma de componentes (%s) no cuadra con POTENCIAL-REALIZADO (%s). "
                "Diferencia: %s (%.2f %%). Revisa la descomposicion."
                % (suma_montos, brecha_total, suma_montos - brecha_total,
                   100.0 * (suma_montos - brecha_total) / brecha_total)
            )

        piso = sum(c.aporte_piso() for c in componentes)
        techo = sum(c.aporte_techo() for c in componentes)

        conocidas = [c for c in componentes if c.medida]
        desconocidas = [c for c in componentes if not c.medida]

        detalle = []
        for c in componentes:
            detalle.append({
                "nombre": c.nombre,
                "monto": c.monto,
                "accesibilidad": c.accesibilidad,
                "medida": c.medida,
                "aporte_piso": round(c.aporte_piso(), 2),
                "aporte_techo": round(c.aporte_techo(), 2),
                "fuente": c.fuente,
            })

        if not desconocidas:
            valor = piso
            return Resultado(
                brecha=valor, piso=valor, techo=techo,
                incertidumbre="Nula",
                confianza="Alta" if len(conocidas) else "Baja",
                componentes=detalle, advertencias=advertencias,
            )

        inc = GapEngine._incertidumbre(techo - piso, techo)
        if desconocidas:
            advertencias.append(
                "%d componente(s) sin accesibilidad medida: %s. Se devuelve rango."
                % (len(desconocidas), ", ".join(c.nombre for c in desconocidas))
            )
        return Resultado(
            brecha=None, piso=piso, techo=techo, incertidumbre=inc,
            confianza="Media" if len(conocidas) > len(desconocidas) else "Baja",
            componentes=detalle, advertencias=advertencias,
        )

    # ------------------------------------------------------------------
    # AUXILIARES
    # ------------------------------------------------------------------
    @staticmethod
    def _incertidumbre(amplitud: float, techo: float) -> str:
        if techo <= 0:
            return "Nula"
        relativa = amplitud / techo
        if relativa <= UMBRAL_BAJA:
            return "Baja"
        if relativa <= UMBRAL_MEDIA:
            return "Media"
        return "Alta"

    @staticmethod
    def acotar(valor: float, piso: float, techo: float) -> float:
        """Recorta un valor al rango conocido. Util para simuladores."""
        return max(piso, min(techo, valor))

    @staticmethod
    def escalar(resultado: Resultado, factor: float) -> Dict:
        """Reescala un resultado ya calculado, sin volver a leer datos.

        Es lo que usan los sliders: mueven un parametro sobre una verdad ya
        calculada, no recalculan la verdad.
        """
        return {
            "piso": resultado.piso * factor,
            "techo": resultado.techo * factor,
            "brecha": (resultado.brecha * factor) if resultado.brecha is not None else None,
            "incertidumbre": resultado.incertidumbre,
            "factor": factor,
        }


# =============================================================================
# ADAPTADOR POLITICA
# =============================================================================
def componentes_politica(blancos: float, nulos: float, caida: float,
                         conversion_blancos: Optional[float] = None,
                         conversion_nulos: Optional[float] = None) -> List[Componente]:
    """Traduce el caso electoral a componentes del motor.

    Cada tipo de voto tiene una accesibilidad distinta y hay que declararla:

      blancos  -> se puede medir la conversion historica del pool
      nulos    -> si en la eleccion siguiente SUBIERON, no convirtieron: 0
      caida    -> no hay contrafactual: desconocida

    Si el llamador no aporta la conversion medida, se deja en None y el motor
    devuelve rango. No se asume un valor por defecto.
    """
    return [
        Componente("blancos", blancos, conversion_blancos,
                   "conversion observada del pool de blancos"),
        Componente("nulos", nulos, conversion_nulos,
                   "conversion observada del pool de nulos"),
        Componente("caida", caida, None,
                   "sin contrafactual: no se sabe cuantos volverian"),
    ]


if __name__ == "__main__":
    print("GAP ENGINE v%s" % VERSION)
    print("Este modulo no se ejecuta solo. Ver gap_engine_demo.py")
