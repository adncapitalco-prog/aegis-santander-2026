# -*- coding: utf-8 -*-
"""
PERFILES DE COMPORTAMIENTO ELECTORAL
====================================

Cinco indicadores por municipio, calculados solo con lo que hay en el vault.
Ninguno se llama "ADN cultural" ni "vector memetico": si no se puede medir con
los datos, no se mide.

LOS CINCO
---------
  VOLATILIDAD    % de puestos que cambiaron de partido lider entre 2023 y 2026
  CASTIGO        cambio en puntos de la tasa de perdida (blanco + nulo + no marcado)
  MOVILIZACION   cambio porcentual de participacion entre 2023 y 2026
  DISPONIBILIDAD 1 - HHI: cuanta cuota esta repartida en opciones menores
  RESILIENCIA    cuota del lider de 2023 que conserva en 2026

UN INDICADOR QUE NO SIRVE
-------------------------
VOLATILIDAD, medido de la forma obvia, da 97 % en casi todos los municipios.
No mide volatilidad: mide que los partidos de una departamental no son los de
una nacional (16 codigos en Asamblea 2023 frente a 68 en Camara 2026, con solo
4 comunes). Se calcula igual porque es lo que el encargo pide, pero el
resultado viaja con esa advertencia y no se usa para comparar municipios.

NO CALCULABLE
-------------
RESILIENCIA exige que el partido lider de 2023 exista tambien en 2026. Cuando
no existe, el valor es None y el informe dice NO CALCULABLE. Inventar un cero
seria afirmar que el partido desaparecio del electorado, y lo que desaparecio
fue la lista.

RENDIMIENTO
-----------
Todo vectorizado con pandas. Sin bucles sobre 300.734 filas.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

COLUMNAS = ["Municipio", "Zona", "Puesto", "Anio_Eleccion", "Corporacion",
            "Codigo_Partido", "Nombre_Partido", "Votos"]
CORP_LOCAL, CORP_NACIONAL = "Asamblea", "Cámara"

CAMPOS = [
    ("volatilidad", "%", "puestos con cambio de partido lider"),
    ("castigo", "pp", "cambio de la tasa de perdida"),
    ("movilizacion", "%", "cambio de participacion"),
    ("disponibilidad", "0-1", "1 menos el indice de Herfindahl"),
    ("resiliencia", "0-1", "cuota del lider de 2023 conservada en 2026"),
]


def _cargar(ruta: str) -> pd.DataFrame:
    if str(ruta).lower().endswith(".parquet"):
        return pd.read_parquet(ruta, columns=COLUMNAS)
    return pd.read_csv(ruta, encoding="utf-8-sig", usecols=COLUMNAS)


def _preparar(ruta: str):
    df = _cargar(ruta)
    df = df.copy()
    df["Votos"] = pd.to_numeric(df["Votos"], errors="coerce").fillna(0).astype(int)
    df["cod"] = pd.to_numeric(df["Codigo_Partido"], errors="coerce")
    df["perdido"] = df["Nombre_Partido"].astype(str).str.contains(
        "Voto no aprovechado", case=False, na=False)
    local = df[(df["Anio_Eleccion"] == "2023") & (df["Corporacion"] == CORP_LOCAL)]
    nacional = df[(df["Anio_Eleccion"] == "2026") & (df["Corporacion"] == CORP_NACIONAL)]
    return local, nacional


def _por_puesto(df: pd.DataFrame) -> pd.DataFrame:
    """Total, perdidos, HHI y partido lider por puesto."""
    llaves = ["Municipio", "Zona", "Puesto"]
    total = df.groupby(llaves)["Votos"].sum().rename("total")
    perdido = df[df["perdido"]].groupby(llaves)["Votos"].sum().rename("perdido")
    base = pd.concat([total, perdido], axis=1).fillna(0).reset_index()

    validos = df[~df["perdido"] & df["cod"].notna()]
    g = validos.groupby(llaves + ["cod"])["Votos"].sum().reset_index()
    suma = g.groupby(llaves)["Votos"].transform("sum")
    g["cuota"] = np.where(suma > 0, g["Votos"] / suma, 0.0)
    hhi = g.groupby(llaves)["cuota"].apply(lambda s: float((s ** 2).sum())).rename("hhi")
    cuota_max = g.groupby(llaves)["cuota"].max().rename("cuota_max")
    lider = g.loc[g.groupby(llaves)["Votos"].idxmax()].set_index(llaves)["cod"].rename("lider")

    return base.merge(pd.concat([hhi, cuota_max, lider], axis=1).reset_index(), on=llaves)


def calcular(ruta_detalle: str) -> Dict:
    """Cinco indicadores por municipio, con marcas de no calculable."""
    local, nacional = _preparar(ruta_detalle)
    a = _por_puesto(local)
    b = _por_puesto(nacional)

    llaves = ["Municipio", "Zona", "Puesto"]
    comun = a.merge(b, on=llaves, suffixes=("_23", "_26"))

    # volatilidad: proporcion de puestos que cambiaron de lider
    cambios = (comun["lider_23"] != comun["lider_26"]).sum()
    volatilidad = 100.0 * cambios / len(comun) if len(comun) else None

    filas = []
    for mun, g in comun.groupby("Municipio"):
        tot23 = float(g["total_23"].sum())
        tot26 = float(g["total_26"].sum())
        per23 = float(g["perdido_23"].sum())
        per26 = float(g["perdido_26"].sum())
        tasa23 = 100.0 * per23 / tot23 if tot23 else 0.0
        tasa26 = 100.0 * per26 / tot26 if tot26 else 0.0
        hhi26 = float(np.average(g["hhi_26"], weights=g["total_26"])) if tot26 else 0.0

        # resiliencia: el lider de 2023, cuanto conserva en 2026
        lider23 = g["lider_23"].mode()
        resiliencia = None
        if len(lider23):
            cod = lider23.iloc[0]
            v23 = float(g.loc[g["lider_23"] == cod, "total_23"].sum())
            b_mun = b[b["Municipio"] == mun]
            fila26 = b_mun[b_mun["lider"] == cod]
            if len(fila26) and v23 > 0:
                v26 = float(fila26["total"].sum())
                resiliencia = round(v26 / v23, 4)

        filas.append({
            "municipio": str(mun),
            "puestos": int(len(g)),
            "volatilidad": None if volatilidad is None else round(volatilidad, 2),
            "castigo": round(tasa26 - tasa23, 2),
            "movilizacion": (round(100.0 * (tot26 - tot23) / tot23, 2)
                             if tot23 else None),
            "disponibilidad": round(1.0 - hhi26, 4),
            "resiliencia": resiliencia,
            "votos_2023": int(tot23),
            "votos_2026": int(tot26),
        })

    filas.sort(key=lambda x: -(x["movilizacion"] or -999))
    no_calc = {c: sum(1 for f in filas if f[c] is None) for c, _, _ in CAMPOS}
    return {
        "municipios": filas,
        "campos": [{"campo": c, "unidad": u, "descripcion": d} for c, u, d in CAMPOS],
        "no_calculables": no_calc,
        "advertencia_volatilidad": (
            "VOLATILIDAD da 97 %% en casi todos los municipios y no distingue "
            "unos de otros: los universos de partida no se solapan (16 codigos "
            "en Asamblea 2023, 68 en Camara 2026, 4 comunes). Se publica porque "
            "se pidio, con esta advertencia al lado. No sirve para comparar "
            "municipios."),
    }


# ===========================================================================
# NARRATIVA
# ===========================================================================
def narrativa(fila: Dict) -> str:
    """Traduce los cinco indicadores a lenguaje llano."""
    partes = []
    castigo = fila["castigo"]
    if castigo is not None:
        if castigo > 5:
            partes.append("Este municipio castiga: la gente que fue a votar y "
                          "no eligio a nadie subio %.1f puntos." % castigo)
        elif castigo < -5:
            partes.append("Este municipio dejo de castigar: los votos que no "
                          "eligen a nadie bajaron %.1f puntos." % abs(castigo))
        else:
            partes.append("El castigo se mantuvo casi igual (%.1f puntos)." % castigo)

    mov = fila["movilizacion"]
    if mov is not None:
        if mov > 10:
            partes.append("Se movilizo: voto %.1f %% mas gente que en 2023." % mov)
        elif mov < -10:
            partes.append("Se quedo en casa: voto %.1f %% menos gente." % abs(mov))
        else:
            partes.append("La participacion cambio poco (%.1f %%)." % mov)

    disp = fila["disponibilidad"]
    if disp is not None:
        if disp > 0.85:
            partes.append("El voto esta repartido: ningun partido domina, hay "
                          "terreno para un actor nuevo.")
        elif disp < 0.6:
            partes.append("El voto esta concentrado: el primero manda y los "
                          "demas compiten por migajas.")

    res = fila["resiliencia"]
    if res is None:
        partes.append("No se puede saber si el ganador de 2023 aguanto: su "
                      "lista no compitio en 2026.")
    elif res >= 0.8:
        partes.append("El ganador de 2023 conservo su base (%.0f %% de sus "
                      "votos)." % (100 * res))
    else:
        partes.append("El ganador de 2023 perdio base: solo conservo %.0f %% "
                      "de sus votos." % (100 * res))
    return " ".join(partes)


def tabla_tecnica(perfiles: Dict, maximo: int = 15) -> List[str]:
    """Tabla de los cinco indicadores con su formula."""
    L = []
    L.append("| Municipio | Puestos | Volatilidad | Castigo | Movilizacion | Disponibilidad | Resiliencia |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    for f in perfiles["municipios"][:maximo]:
        def celda(v, fmt):
            return "NO CALC." if v is None else fmt % v
        L.append("| %s | %d | %s | %s | %s | %s | %s |" % (
            f["municipio"], f["puestos"],
            celda(f["volatilidad"], "%.1f %%"),
            celda(f["castigo"], "%+.2f pp"),
            celda(f["movilizacion"], "%+.1f %%"),
            celda(f["disponibilidad"], "%.4f"),
            celda(f["resiliencia"], "%.2f")))
    L.append("")
    L.append("**Formulas**")
    L.append("")
    L.append("- Volatilidad = puestos con partido lider distinto entre años / "
             "puestos comparables x 100")
    L.append("- Castigo = tasa de perdida 2026 - tasa de perdida 2023 (puntos "
             "porcentuales)")
    L.append("- Movilizacion = (votos totales 2026 / votos totales 2023 - 1) x 100")
    L.append("- Disponibilidad = 1 - HHI, con HHI = suma de las cuotas al cuadrado")
    L.append("- Resiliencia = votos 2026 del lider de 2023 / votos 2023 de ese "
             "mismo partido")
    L.append("")
    L.append("*%s*" % perfiles["advertencia_volatilidad"])
    return L
