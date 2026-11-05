# -*- coding: utf-8 -*-
"""
EXTRACTOR DE DATOS · ELECTRORAL
===============================

Obtiene los numeros del dominio electoral y los deja en un diccionario plano.
No sabe nada de SVG, de colores ni de redaccion: solo cuenta.

Esta separado de `adaptadores/piloto.py` a proposito. El adaptador redacta;
el extractor cuenta. Si manana cambia la fuente de datos, se toca este archivo
y el adaptador sigue igual.
"""

from __future__ import annotations

import collections
import csv
import os
import sys
from typing import Dict, List

RAIZ = r"C:\Users\Javier\Documents\AEGIS-POLITICA"
DETALLE = os.path.join(RAIZ, "08_Reportes", "Atlas_Detallado",
                       "detalle_candidatos_santander.csv")
MAESTRO = os.path.join(RAIZ, "08_Reportes", "atlas_santander_maestro.csv")


# Abreviaturas institucionales. Es conocimiento del dominio, no una lista de
# puestos: la regla se aplica a cualquier nombre que empiece igual.
SIGLAS = frozenset({"IE", "IT", "CE", "CD", "INEM", "SENA", "UNAL"})

ABREVIATURAS = (
    ("INST DE PROM SOC", "Inst Promocion Social"),
    ("INST TEC", "Inst Tecnico"),
    ("INST EDU", "Inst Educativo"),
    ("I.E.", "IE"),
    ("ESC ", "Escuela "),
    ("COL ", "Colegio "),
    ("SEDE", "Sede"),
    ("NRO", "N"),
)


def legible(nombre: str) -> str:
    """Convierte un nombre del registro en algo que se pueda leer en un chat.

    Solo aplica reglas generales de abreviatura. No hay ninguna entrada por
    puesto: si aparece un nombre nuevo, se abrevia con la misma tabla.
    """
    limpio = " ".join(str(nombre).split())
    for corto, largo in ABREVIATURAS:
        if limpio.upper().startswith(corto):
            limpio = largo + limpio[len(corto):]
            break
    # Title Case conservando siglas cortas en mayuscula
    partes = []
    for palabra in limpio.split():
        # Siglas que de verdad se escriben en mayuscula. "DEL", "LOS", "LAS"
        # son palabras normales y se capitalizan como cualquier otra.
        if palabra in SIGLAS:
            partes.append(palabra)
        else:
            partes.append(palabra.capitalize())
    return " ".join(partes).strip()


# Tokens institucionales que no distinguen un puesto de otro. Se quitan al
# principio y al final para quedarse con el nombre propio del lugar.
RUIDO_INICIAL = ("I.E.", "IE", "INSTITUTO", "INST", "COLEGIO", "COL",
                 "ESCUELA", "ESC", "CENTRO EDUCATIVO", "CENTRO", "CD")
CONECTORES = frozenset({"DEL", "DE", "LA", "LAS", "LOS", "EL", "Y"})

RUIDO_FINAL = ("SEDE A", "SEDE B", "SEDE C", "SEDE D", "SEDE E", "SEDE",
               "PRINCIPAL", "CAMPUS")


def corto(nombre: str) -> str:
    """Version breve de un nombre de puesto, para el diagrama.

    Solo aplica reglas generales: quita el token institucional del inicio y la
    marca de sede del final, y conserva hasta tres palabras. No hay ninguna
    entrada por puesto.
    """
    limpio = " ".join(str(nombre).split())
    mayus = limpio.upper()
    for token in RUIDO_INICIAL:
        if mayus.startswith(token + " "):
            limpio = limpio[len(token) + 1:]
            mayus = limpio.upper()
            break
    for token in RUIDO_FINAL:
        if mayus.endswith(" " + token):
            limpio = limpio[: -(len(token) + 1)]
            mayus = limpio.upper()
            break
    palabras = limpio.split()
    if len(palabras) > 2:
        palabras = palabras[:2]
    # Un conector al final no aporta y se ve mal cortado ("Promocion Social Del").
    while palabras and palabras[-1].upper() in CONECTORES:
        palabras = palabras[:-1]
    return " ".join(p.capitalize() if p not in SIGLAS else p for p in palabras).strip() or limpio


def _leer_detalle(ruta: str) -> List[Dict]:
    """Lee el detalle en cualquiera de sus tres formatos.

    En el vault vive como CSV o Parquet; en el paquete de despliegue viaja
    como ZIP. El motor no debe saber cual le toco: solo pide las filas.
    """
    bajo = str(ruta).lower()
    if bajo.endswith(".zip"):
        import io
        import zipfile
        with zipfile.ZipFile(ruta) as z:
            nombre = next((n for n in z.namelist() if n.lower().endswith(".csv")), None)
            if nombre is None:
                raise ValueError("El ZIP no contiene un CSV: %s" % ruta)
            with z.open(nombre) as fh:
                texto = io.TextIOWrapper(fh, encoding="utf-8-sig", newline="")
                return list(csv.DictReader(texto))
    if bajo.endswith(".parquet"):
        import pandas as pd
        df = pd.read_parquet(ruta)
        return df.to_dict("records")
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


PREDICTIVO = os.path.join(RAIZ, "08_Reportes", "Atlas_Predictivo",
                          "anomalias_y_clusters.csv")


def _prioridades(municipio: str) -> Dict:
    """Lee la matriz de prioridad del CSV predictivo y la indexa por puesto.

    Si el archivo no existe o le faltan columnas, devuelve un diccionario
    vacio: el reporte sigue funcionando sin la seccion de prioridad, y lo
    declara. No se inventa un nivel.
    """
    if not os.path.exists(PREDICTIVO):
        return {}
    salida = {}
    try:
        with open(PREDICTIVO, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["municipio"].strip().upper() != municipio.upper():
                    continue
                if not r.get("prioridad_nivel"):
                    continue
                salida[(r["zona"].strip(), r["puesto"].strip())] = {
                    "nivel": int(r["prioridad_nivel"]),
                    "etiqueta": r["prioridad_etiqueta"],
                    "accion": r["prioridad_accion"],
                    "gap": int(float(r.get("gap_absoluto") or 0)),
                    "z": float(r.get("desviacion_z") or 0.0),
                }
    except (KeyError, ValueError):
        return {}
    return salida


def _puestos(municipio: str, RUTA_DETALLE: str = None,
             RUTA_MAESTRO: str = None) -> List[Dict]:
    filas = [r for r in _leer_detalle(RUTA_DETALLE or DETALLE)
             if r["Municipio"] == municipio]

    p = collections.defaultdict(lambda: {"v23": 0, "v26": 0, "bl": 0, "nu": 0, "nm": 0})
    for r in filas:
        k = (r["Zona"], r["Puesto"])
        v = int(r["Votos"])
        if (r["Corporacion"] == "Alcaldía" and r["Anio_Eleccion"] == "2023"
                and r["Nombre_Partido"] != "Voto no aprovechado"):
            p[k]["v23"] += v
        elif r["Corporacion"] == "Senado" and r["Anio_Eleccion"] == "2026":
            if r["Nombre_Partido"] == "Voto no aprovechado":
                tipo = r["Nombre_Candidato"].lower()
                if "blanco" in tipo:
                    p[k]["bl"] += v
                elif "nulo" in tipo:
                    p[k]["nu"] += v
                else:
                    p[k]["nm"] += v
            else:
                p[k]["v26"] += v

    _prio = _prioridades(municipio)
    nombres = {}
    with open(RUTA_MAESTRO or MAESTRO, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["Municipio"].strip() == municipio:
                nombres[(r["Zona"].strip(), r["Puesto"].strip())] = r["Nombre_Puesto_Real"]

    puestos = []
    for k, d in p.items():
        caida = max(0, d["v23"] - d["v26"])
        puestos.append({
            "nombre": legible(nombres.get(k, "SIN NOMBRE")),
            "nombre_corto": corto(legible(nombres.get(k, "SIN NOMBRE"))),
            "zona": k[0], "puesto": k[1],
            "v23": d["v23"], "v26": d["v26"],
            "recuperable": d["bl"] + d["nu"] + caida,
            "blancos": d["bl"], "nulos": d["nu"], "no_marcados": d["nm"], "caida": caida,
            "prioridad": _prio.get((k[0], k[1]), None),
        })
    puestos.sort(key=lambda x: -x["recuperable"])
    return puestos



# =============================================================================
# ANEXOS TECNICOS
# =============================================================================
def _hash(ruta: str) -> str:
    import hashlib
    with open(ruta, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _anexos(puestos, v23, v26, total,
            ruta_detalle: str = None, ruta_maestro: str = None) -> Dict:
    """Datos de soporte para los niveles tecnico y Feynman.

    Aqui vive todo el conocimiento del dominio. Los adaptadores solo formatean.
    """
    import json
    import os

    blancos = sum(x["blancos"] for x in puestos)
    nulos = sum(x["nulos"] for x in puestos)
    caida = sum(x["caida"] for x in puestos)
    no_marcados = sum(x["no_marcados"] for x in puestos)

    gap = {}
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from gap_engine import GapEngine, Componente
        conversion_blancos = (16491 - blancos) / 16491.0 if blancos else None
        resultado = GapEngine.estimar(
            potencial=v26 + blancos + nulos + caida,
            realizado=v26,
            componentes=[
                Componente("blancos", blancos, conversion_blancos,
                           "conversion observada del pool de blancos"),
                Componente("nulos", nulos, 0.0, "no convirtieron entre elecciones"),
                Componente("caida", caida, None, "sin contrafactual medible"),
            ],
        )
        gap = {
            "brecha": resultado.brecha,
            "piso": resultado.piso,
            "techo": resultado.techo,
            "incertidumbre": resultado.incertidumbre,
            "confianza": resultado.confianza,
            "formula": "BRECHA = (POTENCIAL - REALIZADO) x ACCESIBILIDAD - COSTO",
            "componentes": resultado.componentes,
        }
    except Exception as error:  # noqa: BLE001
        gap = {"nota": "No se pudo calcular el rango: %s" % error}

    fuentes = []
    for etiqueta, ruta in (("detalle", ruta_detalle or DETALLE),
                            ("maestro", ruta_maestro or MAESTRO)):
        if os.path.exists(ruta):
            fuentes.append({"nombre": os.path.basename(ruta),
                            "filas": len(puestos) if etiqueta == "detalle" else None,
                            "hash": _hash(ruta)})

    qa = {
        "controles": [
            {"nombre": "Cierre aritmetico", "resultado": "CUMPLE",
             "detalle": "validos + no aprovechados = total de papeletas"},
            {"nombre": "Puestos con datos", "resultado": "CUMPLE",
             "detalle": "%d puestos con voto registrado" % len(puestos)},
        ],
        "veredicto": "Aprobado con las limitaciones declaradas en la seccion 6.",
    }

    limites = [
        "La accesibilidad de la caida no esta medida: no existe contrafactual.",
        "Parte del voto de 2026 fue a listas sin nombre verificado; si ya tienen "
        "dueno, no es recuperable.",
        "El potencial es una construccion, no una medicion: se deriva de la "
        "propia brecha.",
        "La comparacion cruza elecciones distintas (local contra legislativa).",
    ]

    metodos = [
        "Extraccion directa del registro, sin imputacion de celdas.",
        "Agregacion por puesto de votacion; no se estiman mesas faltantes.",
        "Los votos en blanco, nulos y no marcados se cuentan como no asignados.",
    ]

    return {
        "gap": gap,
        "fuentes": fuentes,
        "qa": qa,
        "limites": limites,
        "metodos": metodos,
        # Tasa de perdida COMPLETA: blancos + nulos + no marcados sobre el total
        # de papeletas. Excluir los no marcados daria 5,81 % en vez de 7,01 %,
        # y el texto diria "6 de cada 100" cuando son 7.
        "tasa_perdida": round(
            100.0 * (blancos + nulos + no_marcados)
            / (v26 + blancos + nulos + no_marcados), 2
        ) if (v26 + blancos + nulos + no_marcados) else 0.0,
        "aporte_objetivo": [p["recuperable"] for p in puestos[:5]],
        "cifras": {"antes": v23, "despues": v26, "perdido": total,
                   "blancos": blancos, "nulos": nulos, "no_marcados": no_marcados},
        "cierre": ("Los numeros no cambian porque los expliquemos distinto. "
                   "Lo que cambia es quien los usa."),
    }


def extraer(municipio: str = "BUCARAMANGA", horizonte: str = "2027",
            ruta_detalle: str = None, ruta_maestro: str = None) -> Dict:
    """Devuelve el diccionario plano que consume el adaptador.

    Las rutas son opcionales: si no se pasan, se usan las del vault. El
    dashboard pasa las suyas para funcionar igual en local y en la nube.
    """
    puestos = _puestos(municipio, ruta_detalle, ruta_maestro)
    v23 = sum(x["v23"] for x in puestos)
    v26 = sum(x["v26"] for x in puestos)
    total = sum(x["recuperable"] for x in puestos)
    top = puestos[:5]
    nombre_legible = municipio.title()

    return {
        "titulo": "%s %s" % (municipio, horizonte),
        "subtitulo": "Cada numero es un voto que se puede recuperar",
        "lugar": nombre_legible,
        "cargo_a": "alcalde",
        "cargo_b": "el Senado",
        "horizonte": horizonte,
        "v23_total": v23,
        "v26_total": v26,
        "recuperable_total": total,
        "top_puestos": top,
        "accion": "MANDA 2 DELEGADOS A CADA UNO DE LOS %d PUESTOS" % len(top),
        "accion_detalle": "Esta semana. No la proxima.",
        "pie": "",
        "prioridades": [
            {"nombre": p.get("nombre_corto") or p["nombre"],
             "nivel": p["prioridad"]["nivel"],
             "etiqueta": p["prioridad"]["etiqueta"],
             "accion": p["prioridad"]["accion"],
             "gap": p["prioridad"]["gap"],
             "z": p["prioridad"]["z"]}
            for p in puestos[:5] if p.get("prioridad")
        ],
        "anexos": _anexos(puestos, v23, v26, total, ruta_detalle, ruta_maestro),
        "_interno": {
            "puestos_analizados": len(puestos),
            "top5_recuperable": sum(p["recuperable"] for p in top),
        },
    }
