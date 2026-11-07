# -*- coding: utf-8 -*-
"""
DINAMICA DE LA EXPECTATIVA · indice de sensibilidad
===================================================

Modulo agnostico al dominio. Recibe unidades con valores historicos y devuelve
cuanto depende cada una de la expectativa futura.

QUE MIDE
--------
La sensibilidad NO es una propiedad absoluta de la unidad: es su posicion
relativa dentro del conjunto. Una unidad con 0,80 no es "muy sensible" en
abstracto; es mas sensible que el 80 % de sus pares.

Esto importa. Un indice presentado como absoluto invita a compararlo entre
departamentos, anos o dominios distintos, y ahi no significa nada.

DE DONDE SALE
-------------
De la volatilidad observada entre periodos. Una unidad cuyo valor se mueve
poco tiene lealtad o inercia; una que se mueve mucho depende de lo que se
espere de ella.

    cambio_t   = |v_t - v_t-1| / max(|v_t-1|, epsilon)
    volatilidad = media de los cambios
    indice      = rango percentil de la volatilidad dentro del conjunto

POR QUE PERCENTIL Y NO MIN-MAX
------------------------------
Min-max hace que un solo valor extremo aplaste al resto. El percentil reparte
las unidades en una escala uniforme y no depende de la magnitud del outlier.
Es la misma decision que se tomo para los umbrales de red y de prioridad.

SIN DEPENDENCIAS PESADAS
------------------------
numpy puro. Sin pandas obligatorio: acepta listas de diccionarios o un
DataFrame (se convierte a listas). Sin scipy, sin sklearn.

LIMITE DECLARADO
----------------
Con dos periodos solo hay UN cambio por unidad. La volatilidad entonces es el
tamano de ese cambio, no una varianza. Con tres o mas periodos hay varianza
real. El modulo declara cuantos periodos recibio.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import numpy as np

EPSILON = 1e-9


# ===========================================================================
# NORMALIZACION
# ===========================================================================
def _percentiles(valores: np.ndarray) -> np.ndarray:
    """Rango percentil de cada valor, en [0,1]. Empates comparten rango."""
    n = len(valores)
    if n == 0:
        return np.array([])
    if n == 1:
        return np.array([0.5])
    orden = np.argsort(np.argsort(valores, kind="stable"), kind="stable")
    return orden.astype(float) / (n - 1)


# ===========================================================================
# NUCLEO
# ===========================================================================
def calcular_sensibilidad(
    datos: Iterable[Dict[str, Any]],
    campo_unidad: str = "unidad",
    campo_periodo: str = "periodo",
    campo_valor: str = "valor",
) -> Dict[str, Any]:
    """Indice de sensibilidad por unidad, en [0,1].

    Parametros
    ----------
    datos          lista de dicts, o DataFrame (se convierte)
    campo_unidad   nombre del campo que identifica la unidad
    campo_periodo  nombre del campo temporal, ordenable
    campo_valor    nombre del campo numerico

    Devuelve
    --------
    {"unidades": [{"unidad", "periodos", "volatilidad", "indice_sensibilidad",
                   "valores"}], "periodos": N, "aviso": str}
    """
    # aceptar DataFrame sin importar pandas
    if hasattr(datos, "to_dict") and hasattr(datos, "columns"):
        registros = datos.to_dict("records")
    else:
        registros = list(datos)

    if not registros:
        return {"unidades": [], "periodos": 0,
                "aviso": "Sin datos: no se puede calcular sensibilidad."}

    # agrupar
    por_unidad: Dict[str, Dict[Any, float]] = {}
    for r in registros:
        try:
            unidad = r[campo_unidad]
            periodo = r[campo_periodo]
            valor = float(r[campo_valor])
        except (KeyError, TypeError, ValueError):
            continue
        por_unidad.setdefault(unidad, {})[periodo] = valor

    if not por_unidad:
        return {"unidades": [], "periodos": 0,
                "aviso": "Ningun registro tenia los tres campos requeridos."}

    periodos = sorted({p for v in por_unidad.values() for p in v})

    crudos = []
    for unidad, serie in por_unidad.items():
        ordenados = [serie[p] for p in periodos if p in serie]
        if len(ordenados) < 2:
            crudos.append((unidad, 0.0, ordenados))
            continue
        cambios = []
        for i in range(1, len(ordenados)):
            base = max(abs(ordenados[i - 1]), EPSILON)
            cambios.append(abs(ordenados[i] - ordenados[i - 1]) / base)
        crudos.append((unidad, float(np.mean(cambios)), ordenados))

    volatilidades = np.array([c[1] for c in crudos], dtype=float)
    indices = _percentiles(volatilidades)

    salida = []
    for i, (unidad, vol, valores) in enumerate(crudos):
        salida.append({
            "unidad": unidad,
            "periodos": len(valores),
            "volatilidad": round(float(vol), 6),
            "indice_sensibilidad": round(float(indices[i]), 4),
            "valores": [round(float(v), 4) for v in valores],
        })
    salida.sort(key=lambda x: -x["indice_sensibilidad"])

    aviso = ""
    if len(periodos) < 3:
        aviso = ("Solo %d periodos: la volatilidad es el tamano de un unico "
                 "cambio, no una varianza. Con tres o mas periodos el indice "
                 "mide dispersion real." % len(periodos))

    return {
        "unidades": salida,
        "periodos": len(periodos),
        "etiquetas_periodo": [str(p) for p in periodos],
        "aviso": aviso,
        "nota_relativa": ("El indice es la posicion de la unidad dentro del "
                          "conjunto, no una propiedad absoluta. Un 0,80 "
                          "significa 'mas sensible que el 80 % de sus pares'."),
    }


def clasificar(sensibilidad: float) -> str:
    """Tramo cualitativo. Cortes en tercios, no en valores fijos de la escala."""
    if sensibilidad is None:
        return "DESCONOCIDA"
    if sensibilidad >= 2.0 / 3.0:
        return "ALTA"
    if sensibilidad >= 1.0 / 3.0:
        return "MEDIA"
    return "BAJA"
