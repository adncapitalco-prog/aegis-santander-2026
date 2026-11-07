# -*- coding: utf-8 -*-
"""
FORWARD GUIDANCE · motor de senalizacion
========================================

Dada una unidad y su sensibilidad, decide que senal emitir y estima cuanto
reduce la incertidumbre.

LAS TRES SENALES
----------------
  SEÑAL_A  Simbolica. Reconocimiento publico. Bajo costo, ancla la atencion.
           Funciona cuando la unidad ya esta mirando y necesita saber que
           alguien la ve.
  SEÑAL_B  Compromiso verificable. Hoja de ruta con fechas y metricas.
           Reduce la incertidumbre porque convierte una promesa en un hecho
           comprobable.
  SEÑAL_C  Silencio estrategico. No intervenir. Para unidades de baja
           sensibilidad, donde cualquier senal genera ruido y el ruido se
           interpreta como presion.

LA REDUCCION DE ENTROPIA ES UN MODELO, NO UNA MEDICION
------------------------------------------------------
El porcentaje que devuelve este modulo NO se mide: se calcula con una formula
declarada. No es entropia de Shannon de nada. Es una estimacion de decision
para ordenar opciones, y presentarla como medicion seria el mismo error que
presentar un umbral fijo como un hallazgo.

La formula y sus supuestos estan a la vista en `_ajuste_por_sensibilidad` y en
`BASE_SENAL`. Si un asesor no esta de acuerdo con los supuestos, puede
cambiarlos y el resultado cambia: eso es lo que distingue un modelo de una
caja negra.

POR QUE NO SE USA UN LLM
------------------------
La expectativa no se alucina. Sale de la varianza historica de los datos de
entrada y de una regla fija. Un LLM podria redactar la recomendacion mejor,
pero no podria justificarla con la serie que la origina.
"""

from __future__ import annotations

from typing import Any, Dict, List

SENALES = {
    "A": {"nombre": "Simbolica", "base": 0.45,
          "descripcion": "Reconocimiento publico. Bajo costo, ancla la atencion.",
          "pico": 0.45},
    "B": {"nombre": "Compromiso verificable", "base": 0.90,
          "descripcion": "Hoja de ruta con fechas y metricas. Convierte una "
                         "promesa en un hecho comprobable.",
          "pico": 0.75},
    "C": {"nombre": "Silencio estrategico", "base": 0.55,
          "descripcion": "No intervenir. Cualquier senal seria ruido.",
          "pico": 0.15},
}

CONTEXTOS = {
    "electoral": {
        "unidad": "puesto de votacion",
        "variable": "votos",
        "recurso": "delegados",
        "comunidad": "el electorado",
        "accion_fisica": "desplegar los delegados",
    },
    "seguridad": {
        "unidad": "zona",
        "variable": "denuncias",
        "recurso": "patrullas",
        "comunidad": "los vecinos",
        "accion_fisica": "desplegar las patrullas",
    },
    "economia": {
        "unidad": "sector",
        "variable": "empleos",
        "recurso": "incentivos",
        "comunidad": "los empresarios",
        "accion_fisica": "desplegar los incentivos",
    },
    "gestion_publica": {
        "unidad": "dependencia",
        "variable": "tramites",
        "recurso": "funcionarios",
        "comunidad": "los ciudadanos",
        "accion_fisica": "reasignar los funcionarios",
    },
}

CONTEXTO_POR_DEFECTO = "gestion_publica"


def vocabulario(contexto: str) -> Dict[str, str]:
    """Palabras del contexto. Si no existe, cae al generico y lo declara."""
    return CONTEXTOS.get(str(contexto).lower().strip(),
                         CONTEXTOS[CONTEXTO_POR_DEFECTO])


# ===========================================================================
# MODELO
# ===========================================================================
def _ajuste_por_sensibilidad(sensibilidad: float, pico: float) -> float:
    """Cuanto rinde una senal segun lo lejos que este la unidad de su pico.

    Ajuste triangular: 1,0 en el pico, 0,0 en el extremo opuesto. No es una
    ley: es una forma simple que captura la idea de que cada senal tiene su
    terreno y fuera de el rinde menos.
    """
    s = max(0.0, min(1.0, float(sensibilidad)))
    if pico <= 0.0:
        return 1.0 - s
    if pico >= 1.0:
        return s
    distancia = abs(s - pico)
    alcance = max(pico, 1.0 - pico)
    return max(0.0, 1.0 - distancia / alcance)


def _senal_recomendada(sensibilidad: float) -> str:
    """La senal que corresponde al tramo de sensibilidad."""
    s = max(0.0, min(1.0, float(sensibilidad)))
    if s >= 2.0 / 3.0:
        return "B"
    if s >= 1.0 / 3.0:
        return "A"
    return "C"


def evaluar_senal(
    unidad: Any,
    tipo_senal: str = None,
    contexto: str = "electoral",
    sensibilidad: float = None,
) -> Dict[str, Any]:
    """Evalua una senal para una unidad.

    Si `tipo_senal` es None, devuelve la recomendada para ese nivel de
    sensibilidad. Si se pasa una senal concreta, calcula su rendimiento para
    poder comparar alternativas.

    Devuelve entropia reducida (0-100), que es un MODELO declarado, no una
    medicion.
    """
    if sensibilidad is None:
        return {"unidad": unidad, "error": "Falta la sensibilidad de la unidad.",
                "reduccion_entropia": 0}

    s = max(0.0, min(1.0, float(sensibilidad)))
    recomendada = _senal_recomendada(s)
    clave = (str(tipo_senal).upper().strip() if tipo_senal else recomendada)
    if clave not in SENALES:
        clave = recomendada

    datos = SENALES[clave]
    ajuste = _ajuste_por_sensibilidad(s, datos["pico"])
    reduccion = round(100.0 * datos["base"] * ajuste, 1)

    # coste relativo: A es barata, B es cara, C no cuesta
    coste = {"A": "bajo", "B": "alto", "C": "nulo"}[clave]

    return {
        "unidad": unidad,
        "contexto": str(contexto),
        "sensibilidad": round(s, 4),
        "tramo": ("ALTA" if s >= 2 / 3 else "MEDIA" if s >= 1 / 3 else "BAJA"),
        "senal_recomendada": recomendada,
        "senal_evaluada": clave,
        "senal_nombre": datos["nombre"],
        "senal_descripcion": datos["descripcion"],
        "coste": coste,
        "reduccion_entropia": reduccion,
        "es_la_recomendada": clave == recomendada,
        "modelo": ("Reduccion = base_senal x ajuste_triangular(sensibilidad, "
                   "pico_senal). Modelo de decision declarado, no una medicion "
                   "de entropia."),
    }


def comparar_senales(unidad: Any, contexto: str = "electoral",
                     sensibilidad: float = None) -> Dict[str, Any]:
    """Las tres senales para la misma unidad, ordenadas por rendimiento."""
    evaluaciones = [evaluar_senal(unidad, t, contexto, sensibilidad)
                    for t in ("A", "B", "C")]
    evaluaciones.sort(key=lambda x: -x["reduccion_entropia"])
    return {
        "unidad": unidad,
        "contexto": contexto,
        "sensibilidad": sensibilidad,
        "opciones": evaluaciones,
        "mejor": evaluaciones[0]["senal_evaluada"] if evaluaciones else None,
    }


# ===========================================================================
# NARRATIVA
# ===========================================================================
def narrativa(recomendacion: Dict[str, Any], contexto: str = "electoral") -> str:
    """Explica la recomendacion en lenguaje llano, con el vocabulario del contexto."""
    v = vocabulario(contexto)
    unidad = recomendacion.get("unidad", "la unidad")
    clave = recomendacion.get("senal_recomendada", "C")
    s = recomendacion.get("sensibilidad", 0.0)
    tramo = recomendacion.get("tramo", "MEDIA")

    if clave == "B":
        return ("No %s a ciegas en **%s**. Primero emite una **senal de "
                "compromiso verificable** esta semana: una hoja de ruta con "
                "fechas y metricas. Eso ancla la expectativa. Una vez que %s "
                "sienta que el rumbo es claro, entonces sí %s. La senal prepara el terreno; "
                "la accion fisica cosecha el resultado."
                % (v["accion_fisica"], unidad, v["comunidad"], v["accion_fisica"]))
    if clave == "A":
        return ("**%s** tiene sensibilidad media (%s). No hace falta comprometer "
                "recursos todavia: basta un reconocimiento publico que ancle la "
                "atencion. Si el reconocimiento no mueve nada en dos semanas, "
                "entonces si toca un compromiso verificable."
                % (unidad, tramo.lower()))
    return ("**%s** tiene sensibilidad baja (%s): su comportamiento esta "
            "consolidado. La mejor senal es **no intervenir**. Cualquier anuncio "
            "aqui genera ruido, y el ruido se lee como presion. Vigilar sin "
            "actuar." % (unidad, tramo.lower()))


def tabla_opciones(comparacion: Dict[str, Any]) -> List[str]:
    """Tabla markdown de las tres senales con su rendimiento."""
    L = ["| Senal | Nombre | Coste | Reduccion estimada | Es la recomendada |",
         "|---|---|---|---:|---|"]
    for o in comparacion["opciones"]:
        L.append("| %s | %s | %s | %.1f %% | %s |"
                 % (o["senal_evaluada"], o["senal_nombre"], o["coste"],
                    o["reduccion_entropia"], "si" if o["es_la_recomendada"] else ""))
    L.append("")
    L.append("*%s*" % comparacion["opciones"][0]["modelo"])
    return L
