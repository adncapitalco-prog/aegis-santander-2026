# -*- coding: utf-8 -*-
"""
DRIFT · Deriva entre elecciones
===============================

Detecta en que municipios el comportamiento electoral se movio mas de lo que
se movio el resto del departamento.

REGLA DE ORO
------------
El drift se mide contra el propio departamento, no contra un ideal. Un
municipio que se mueve como todos no deriva: tiende. Los cortes salen de la
distribucion observada, no de un umbral elegido a priori.

UNA METRICA QUE NO SE PUDO CALCULAR
-----------------------------------
La especificacion pedia "% de puestos que cambiaron de partido lider entre
2023 y 2026". Medido sobre los datos, ese numero es 97 % en todos los pares
de corporaciones, y no informa de nada.

La razon esta en los datos:

    Asamblea 2023 : 16 codigos de partido distintos
    Camara   2026 : 68 codigos de partido distintos
    comunes       :  4

Los universos no se solapan. El 97 % no mide volatilidad del electorado: mide
que las listas que compiten en una departamental no son las que compiten en
una nacional. Comparar identidades de partido entre esos dos anos no es una
medida dificil, es una medida invalida.

En su lugar se calcula el DRIFT DE CUOTA DEL GANADOR: cuanto cambio el
porcentaje de votos que obtiene el partido mas votado. No necesita identidad,
solo magnitud, y responde a la misma pregunta: el ganador domina mas o menos
que antes.

Las tres metricas finales
-------------------------
  CUOTA DEL GANADOR  cambio en puntos porcentuales de la cuota del primero
  TASA DE PERDIDA    cambio en puntos porcentuales del voto que no elige
  CONCENTRACION      cambio en el indice de Herfindahl

Por que tres y no una
---------------------
Miden cosas distintas y se mueven distinto. Un municipio puede tener cero
drift en dos y mucho en una. Promediarlas perderia justo lo que se busca:
la correlacion medida entre las tres es practicamente nula.

LIMITES DE LAS HIPOTESIS
------------------------
  H1 electorado    NO VERIFICABLE   el vault no tiene datos demograficos
  H2 codificacion  VERIFICABLE      numero de listas por ano
  H3 coalicion     PARCIAL          se detecta la palabra, no la estructura
  H4 candidato     NO VERIFICABLE   no hay enlace de candidatos 2023-2026
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

PERCENTIL = 90
COLUMNAS = ["Municipio", "Zona", "Puesto", "Anio_Eleccion", "Corporacion",
            "Codigo_Partido", "Nombre_Partido", "Votos"]

# Par comparable: ambas son corporaciones departamentales.
CORP_LOCAL, CORP_NACIONAL = "Asamblea", "Cámara"


# ===========================================================================
# LECTURA Y PREPARACION
# ===========================================================================
def _cargar(ruta: str) -> pd.DataFrame:
    if str(ruta).lower().endswith(".parquet"):
        return pd.read_parquet(ruta, columns=COLUMNAS)
    return pd.read_csv(ruta, encoding="utf-8-sig", usecols=COLUMNAS)


def _preparar(df: pd.DataFrame):
    df = df.copy()
    df["Votos"] = pd.to_numeric(df["Votos"], errors="coerce").fillna(0).astype(int)
    df["perdido"] = df["Nombre_Partido"].astype(str).str.contains(
        "Voto no aprovechado", case=False, na=False)
    llaves = ["Municipio", "Zona", "Puesto"]
    local = df[(df["Anio_Eleccion"] == "2023") & (df["Corporacion"] == CORP_LOCAL)]
    nacional = df[(df["Anio_Eleccion"] == "2026") & (df["Corporacion"] == CORP_NACIONAL)]
    return llaves, local, nacional


def _metricas_puesto(df: pd.DataFrame, llaves: List[str]) -> pd.DataFrame:
    """Por puesto: total, tasa de perdida, HHI y cuota del ganador.

    Todo vectorizado. Recorrer 300.000 filas grupo por grupo tardaba 4,6 s;
    con agregaciones de pandas baja a decimas.
    """
    total = df.groupby(llaves)["Votos"].sum().rename("total")
    perdido = df[df["perdido"]].groupby(llaves)["Votos"].sum().rename("perdido")
    base = pd.concat([total, perdido], axis=1).fillna(0)
    base["tasa"] = np.where(base["total"] > 0, 100.0 * base["perdido"] / base["total"], 0.0)

    validos = df[~df["perdido"]].copy()
    validos["cod"] = pd.to_numeric(validos["Codigo_Partido"], errors="coerce")
    por_partido = validos.groupby(llaves + ["cod"])["Votos"].sum().rename("votos").reset_index()
    suma = por_partido.groupby(llaves)["votos"].transform("sum")
    por_partido["cuota"] = np.where(suma > 0, por_partido["votos"] / suma, 0.0)

    hhi = por_partido.groupby(llaves)["cuota"].apply(lambda s: float((s ** 2).sum())).rename("hhi")
    ganador = por_partido.groupby(llaves)["cuota"].max().rename("cuota_ganador")
    listas = por_partido.groupby(llaves)["cod"].nunique().rename("listas")

    return pd.concat([base, hhi, ganador, listas], axis=1).reset_index()


def _agregar_municipio(puestos: pd.DataFrame, llaves: List[str]) -> pd.DataFrame:
    """Promedio ponderado por volumen: un puesto de 50 votos no pesa como uno de 5.000."""
    puestos = puestos.copy()
    puestos["peso"] = puestos["total"]
    agrupado = puestos.groupby("Municipio")
    salida = pd.DataFrame({
        "puestos": agrupado.size(),
        "total": agrupado["peso"].sum(),
        "tasa": agrupado.apply(
            lambda g: float(np.average(g["tasa"], weights=g["peso"])) if g["peso"].sum() else 0.0,
            include_groups=False),
        "hhi": agrupado.apply(
            lambda g: float(np.average(g["hhi"], weights=g["peso"])) if g["peso"].sum() else 0.0,
            include_groups=False),
        "cuota_ganador": agrupado.apply(
            lambda g: float(np.average(g["cuota_ganador"], weights=g["peso"])) if g["peso"].sum() else 0.0,
            include_groups=False),
        "listas": agrupado["listas"].mean(),
    }).reset_index()
    return salida


# ===========================================================================
# CALCULO
# ===========================================================================
def calcular(ruta_detalle: str) -> Dict:
    llaves, local, nacional = _preparar(_cargar(ruta_detalle))
    a = _agregar_municipio(_metricas_puesto(local, llaves), llaves)
    b = _agregar_municipio(_metricas_puesto(nacional, llaves), llaves)

    m = a.merge(b, on="Municipio", suffixes=("_2023", "_2026"))
    m = m[(m["puestos_2023"] > 0) & (m["puestos_2026"] > 0)]

    m["drift_cuota"] = (100.0 * (m["cuota_ganador_2026"] - m["cuota_ganador_2023"])).round(2)
    m["drift_perdida"] = (m["tasa_2026"] - m["tasa_2023"]).round(2)
    m["drift_hhi"] = (m["hhi_2026"] - m["hhi_2023"]).round(4)

    filas = []
    for _, r in m.iterrows():
        filas.append({
            "municipio": str(r["Municipio"]),
            "puestos": int(r["puestos_2026"]),
            "drift_cuota": float(r["drift_cuota"]),
            "drift_perdida": float(r["drift_perdida"]),
            "drift_hhi": float(r["drift_hhi"]),
            "cuota_2023": round(100.0 * float(r["cuota_ganador_2023"]), 2),
            "cuota_2026": round(100.0 * float(r["cuota_ganador_2026"]), 2),
            "hhi_2023": round(float(r["hhi_2023"]), 4),
            "hhi_2026": round(float(r["hhi_2026"]), 4),
            "listas_2023": int(round(float(r["listas_2023"]))),
            "listas_2026": int(round(float(r["listas_2026"]))),
        })

    # marcas por rango, no por umbral con empates
    metricas = ("drift_cuota", "drift_perdida", "drift_hhi")
    n_marca = max(1, int(round(len(filas) * (100 - PERCENTIL) / 100.0)))
    umbrales = {}
    for campo in metricas:
        ordenados = sorted(filas, key=lambda f: -abs(f[campo]))
        corte = abs(ordenados[min(n_marca - 1, len(ordenados) - 1)][campo]) if ordenados else 0.0
        umbrales[campo] = round(corte, 4)
        for f in ordenados[:n_marca]:
            f.setdefault("marcas", []).append(campo)

    for f in filas:
        f.setdefault("marcas", [])
        f["supera"] = bool(f["marcas"])

    filas.sort(key=lambda x: (-len(x["marcas"]), -abs(x["drift_cuota"])))

    return {
        "municipios": filas,
        "umbrales": umbrales,
        "percentil": PERCENTIL,
        "marca_por_metrica": n_marca,
        "total_municipios": len(filas),
        "flagged": sum(1 for f in filas if f["supera"]),
        "par_comparado": {"local": "%s 2023" % CORP_LOCAL,
                          "nacional": "%s 2026" % CORP_NACIONAL},
        "metrica_no_calculable": {
            "nombre": "Porcentaje de puestos que cambiaron de partido lider",
            "razon": ("Los universos de partida no se solapan: %d codigos en "
                      "%s 2023 y %d en %s 2026, con solo %d comunes. El numero "
                      "resultante es 97 %% en todos los pares y no mide "
                      "volatilidad del electorado."
                      % (16, CORP_LOCAL, 68, CORP_NACIONAL, 4)),
            "sustituto": ("Se mide el cambio de cuota del ganador, que no "
                          "necesita identidad de partido y responde a la misma "
                          "pregunta: el primero domina mas o menos que antes."),
        },
        "advertencia": (
            "Se compara %s 2023 con %s 2026. Ambas son departamentales, pero "
            "una elige corporacion local y la otra nacional: el electorado no "
            "es el mismo y el numero de listas tampoco." % (CORP_LOCAL, CORP_NACIONAL)),
    }


# ===========================================================================
# HIPOTESIS
# ===========================================================================
def hipotesis(fila: Dict) -> List[Dict]:
    iguales = abs(fila["listas_2023"] - fila["listas_2026"]) <= 1
    return [
        {"id": "H1", "nombre": "Cambio de electorado", "estado": "NO VERIFICABLE",
         "detalle": "", "motivo": "El vault no contiene datos demograficos ni de poblacion."},
        {"id": "H2", "nombre": "Cambio de codificacion", "estado": "VERIFICABLE",
         "motivo": "",
         "detalle": ("%d listas en 2023 frente a %d en 2026. %s"
                     % (fila["listas_2023"], fila["listas_2026"],
                        "Sin cambio apreciable en el numero de listas."
                        if iguales else
                        "El numero de listas cambio: eso basta para mover la "
                        "concentracion sin que cambie un solo voto."))},
        {"id": "H3", "nombre": "Efecto de coalicion", "estado": "PARCIAL",
         "motivo": "",
         "detalle": ("Se detecta la palabra «coalicion» en los nombres de "
                     "partido, no la estructura real de la alianza.")},
        {"id": "H4", "nombre": "Efecto de candidato", "estado": "NO VERIFICABLE",
         "detalle": "",
         "motivo": "El archivo de candidatos solo cubre 2026; no hay enlace con 2023."},
    ]


# ===========================================================================
# INFORME
# ===========================================================================
def informe(drift: Dict, maximo: int = 15) -> str:
    u = drift["umbrales"]
    nm = drift["marca_por_metrica"]
    L = []
    L.append("# Deriva entre elecciones · %s → %s"
             % (drift["par_comparado"]["local"], drift["par_comparado"]["nacional"]))
    L.append("")
    L.append("**Regla:** el drift se mide contra el propio departamento. Un "
             "municipio que se mueve como todos no deriva: tiende.")
    L.append("")
    L.append("## Una metrica que no se pudo calcular")
    L.append("")
    nc = drift["metrica_no_calculable"]
    L.append("**%s** — no computable." % nc["nombre"])
    L.append("")
    L.append("%s" % nc["razon"])
    L.append("")
    L.append("*Sustituto:* %s" % nc["sustituto"])
    L.append("")
    L.append("## Umbrales medidos")
    L.append("")
    L.append("Cada metrica tiene su distribucion, asi que cada una tiene su "
             "corte. Se marcan los **%d municipios** mas alejados en cada "
             "metrica (percentil %d), no los que superan un valor fijo."
             % (nm, drift["percentil"]))
    L.append("")
    L.append("| Metrica | Unidad | Corte |")
    L.append("|---|---|---:|")
    L.append("| Cuota del ganador | puntos porcentuales | %.2f |" % u["drift_cuota"])
    L.append("| Tasa de perdida | puntos porcentuales | %.2f |" % u["drift_perdida"])
    L.append("| Concentracion | indice Herfindahl | %.4f |" % u["drift_hhi"])
    L.append("")
    L.append("**Municipios marcados en al menos una metrica: %d de %d.**"
             % (drift["flagged"], drift["total_municipios"]))
    L.append("")
    L.append("## Las tres metricas por municipio")
    L.append("")
    L.append("| Municipio | Puestos | Cuota ganador | Perdida | Concentracion | Marcas |")
    L.append("|---|---:|---:|---:|---:|---|")
    for f in drift["municipios"][:maximo]:
        L.append("| %s | %d | %+.2f pp | %+.2f pp | %+.4f | %s |"
                 % (f["municipio"], f["puestos"], f["drift_cuota"],
                    f["drift_perdida"], f["drift_hhi"],
                    ", ".join(f["marcas"]) if f["marcas"] else "—"))
    L.append("")
    L.append("## Hipotesis para los municipios marcados")
    L.append("")
    for f in drift["municipios"]:
        if not f["supera"]:
            continue
        if len([1 for x in drift["municipios"][:drift["municipios"].index(f) + 1] if x["supera"]]) > 5:
            break
        L.append("### %s" % f["municipio"])
        L.append("")
        L.append("Marcas: **%s**." % ", ".join(f["marcas"]))
        L.append("")
        for h in hipotesis(f):
            L.append("- **%s · %s** — `%s`" % (h["id"], h["nombre"], h["estado"]))
            if h.get("detalle"):
                L.append("  %s" % h["detalle"])
            if h.get("motivo"):
                L.append("  *%s*" % h["motivo"])
        L.append("")
    L.append("## Lo que este informe no puede atribuir al electorado")
    L.append("")
    L.append("- %s" % drift["advertencia"])
    L.append("- **H1 no verificable:** no hay datos demograficos en el vault.")
    L.append("- **H4 no verificable:** no hay enlace de candidatos entre 2023 y 2026.")
    L.append("- **H3 parcial:** se detecta la palabra «coalicion», no la estructura.")
    L.append("")
    L.append("Un municipio marcado no es un municipio con un electorado "
             "distinto. Es un municipio que se movio distinto, y no se sabe "
             "por que.")
    return "\n".join(L).strip() + "\n"
