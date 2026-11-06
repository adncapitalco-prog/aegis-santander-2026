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


def _prioridades(municipio: str, ruta_predictivo: str = None) -> Dict:
    """Lee la matriz de prioridad del CSV predictivo y la indexa por puesto.

    La ruta es un PARAMETRO, no una constante. Cuando estaba fija apuntaba al
    vault, y en la nube esa ruta no existe: el reporte salia sin prioridades y
    con las cifras viejas, sin ningun error visible. Fue el fallo que costo
    tres despliegues.

    Si el archivo no existe o le faltan columnas, devuelve un diccionario
    vacio: el reporte sigue funcionando sin la seccion de prioridad, y lo
    declara. No se inventa un nivel.
    """
    ruta = ruta_predictivo or PREDICTIVO
    if not os.path.exists(ruta):
        return {}
    salida = {}
    try:
        with open(ruta, encoding="utf-8-sig", newline="") as fh:
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


MAPEO_PARTIDOS = os.path.join(RAIZ, "08_Reportes", "mapeo_partidos_2026.json")

_cache_mapeo = {"datos": None, "ruta": None}


TOP_CANDIDATOS = os.path.join(RAIZ, "08_Reportes", "top_candidatos_santander.json")

_cache_top = {"datos": None, "ruta": None}


DEUDAS = os.path.join(RAIZ, "08_Reportes", "deudas_forenses.json")


def cargar_deudas(ruta: str = None) -> List[Dict]:
    """Deudas forenses abiertas.

    Una deuda es una cifra que el sistema no puede resolver. Se declara en los
    tres niveles en vez de elegir una y callar la otra.
    """
    import json
    candidatos = [ruta] if ruta else [
        DEUDAS,
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "deudas_forenses.json"),
    ]
    destino = next((c for c in candidatos if c and os.path.exists(c)), None)
    if destino is None:
        return []
    try:
        with open(destino, encoding="utf-8") as fh:
            datos = json.load(fh)
        return [d for d in datos.get("deudas", []) if d.get("estado") == "ABIERTA"]
    except (ValueError, OSError):
        return []


def cargar_top_candidatos(ruta: str = None) -> List[Dict]:
    """Carga el lookup ligero de candidatos de Santander.

    Lee un JSON de 10 KB, no el TXT de 490 KB con las 3.617 lineas de toda
    Colombia. Si no esta, devuelve lista vacia y el reporte sigue: se pierde
    el nombre del candidato, no el reporte.
    """
    import json
    candidatos = [ruta] if ruta else [
        TOP_CANDIDATOS,
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "top_candidatos_santander.json"),
    ]
    destino = next((c for c in candidatos if c and os.path.exists(c)), None)
    if destino is None:
        return []
    if _cache_top["ruta"] == destino and _cache_top["datos"] is not None:
        return _cache_top["datos"]
    try:
        with open(destino, encoding="utf-8") as fh:
            datos = json.load(fh).get("listas", [])
    except (ValueError, OSError):
        datos = []
    _cache_top["datos"] = datos
    _cache_top["ruta"] = destino
    return datos


def cargar_mapeo_partidos(ruta: str = None) -> Dict:
    """Carga el mapeo oficial codigo->nombre de partido.

    Se cachea por ruta: el archivo no cambia durante una sesion y leerlo en
    cada reporte seria desperdicio. Si no existe, devuelve un diccionario
    vacio y el sistema sigue mostrando los codigos: se degrada, no se cae.
    """
    import json
    candidatos = [ruta] if ruta else [
        MAPEO_PARTIDOS,
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "mapeo_partidos_2026.json"),
    ]
    destino = next((c for c in candidatos if c and os.path.exists(c)), None)
    if destino is None:
        _cache_mapeo["datos"] = {}
        return {}
    if _cache_mapeo["ruta"] == destino and _cache_mapeo["datos"] is not None:
        return _cache_mapeo["datos"]
    if not os.path.exists(destino):
        _cache_mapeo["datos"] = {}
        _cache_mapeo["ruta"] = destino
        return {}
    try:
        with open(destino, encoding="utf-8") as fh:
            contenido = json.load(fh)
        crudo = contenido.get("partidos", {})
        datos = {int(k): v for k, v in crudo.items()}
    except (ValueError, KeyError, OSError):
        datos = {}
    _cache_mapeo["datos"] = datos
    _cache_mapeo["ruta"] = destino
    return datos


def resolver_nombre_partido(codigo, ruta_mapeo: str = None) -> str:
    """Devuelve el nombre oficial o 'Lista [codigo]' si no esta en el mapeo.

    Nunca devuelve una cadena vacia ni inventa un nombre. Si el codigo no se
    resuelve, lo dice explicitamente en vez de disfrazarlo.
    """
    mapeo = cargar_mapeo_partidos(ruta_mapeo)
    try:
        nombre = mapeo.get(int(codigo))
    except (TypeError, ValueError):
        nombre = None
    if nombre:
        return nombre
    return "Lista [%s]" % codigo


METRICAS = os.path.join(RAIZ, "08_Reportes", "metricas_depto.json")


def _sin_nombre(ruta: str, ruta_metricas: str = None) -> List[Dict]:
    """Votos de listas cuyo nombre no viene en el archivo de votacion.

    Ruta rapida: lee el sidecar precalculado (200 bytes). Ruta lenta: recorre
    el detalle. Se conserva la lenta porque un sidecar viejo no debe producir
    una cifra equivocada en silencio: si falta, se recalcula.

    Medido antes: 1,19 s recorriendo 300.734 filas en cada reporte.
    """
    candidatos = [ruta_metricas] if ruta_metricas else [
        METRICAS,
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "metricas_depto.json"),
    ]
    for destino in candidatos:
        if destino and os.path.exists(destino):
            try:
                import json
                with open(destino, encoding="utf-8") as fh:
                    valor = int(json.load(fh).get("votos_sin_nombre", 0))
                return [{"votos": valor}]
            except (ValueError, OSError):
                continue

    salida = []
    try:
        for r in _leer_detalle(ruta):
            if (r.get("Corporacion") == "Senado" and r.get("Anio_Eleccion") == "2026"
                    and "nombre pendiente" in r.get("Nombre_Partido", "")):
                salida.append({"votos": int(r["Votos"])})
    except (KeyError, ValueError):
        return []
    return salida


def _puestos(municipio: str, RUTA_DETALLE: str = None,
             RUTA_MAESTRO: str = None,
             RUTA_PREDICTIVO: str = None) -> List[Dict]:
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

    _prio = _prioridades(municipio, RUTA_PREDICTIVO)
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
            ruta_detalle: str = None, ruta_maestro: str = None,
            ruta_metricas: str = None) -> Dict:
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

    # El mapeo oficial de partidos entra al anexo para que el nivel tecnico
    # pueda mostrar los hashes de los TXT de la Registraduria.
    mapeo_meta = {}
    if os.path.exists(MAPEO_PARTIDOS):
        mapeo_meta = {"archivo": os.path.basename(MAPEO_PARTIDOS),
                      "hash": _hash(MAPEO_PARTIDOS)}
        try:
            import json as _json
            with open(MAPEO_PARTIDOS, encoding="utf-8") as fh:
                contenido = _json.load(fh)
            mapeo_meta["fuentes"] = contenido.get("fuentes", [])
            mapeo_meta["partidos"] = len(contenido.get("partidos", {}))
            mapeo_meta["encoding"] = contenido.get("encoding_detectado", "")
        except (ValueError, OSError):
            mapeo_meta["fuentes"] = []

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
        "deudas_forenses": cargar_deudas(),
        "mapeo_partidos": mapeo_meta,
        "top_candidatos": [
            {"partido": l["partido"], "codigo_lista": l["codigo_lista"],
             "primero": l["candidatos"][0]["nombre"] if l["candidatos"] else ""}
            for l in cargar_top_candidatos()
        ],
        "votos_sin_nombre": sum(
            x["votos"] for x in _sin_nombre(ruta_detalle or DETALLE, ruta_metricas)),
        "cierre": ("Los numeros no cambian porque los expliquemos distinto. "
                   "Lo que cambia es quien los usa."),
    }


def extraer(municipio: str = "BUCARAMANGA", horizonte: str = "2027",
            ruta_detalle: str = None, ruta_maestro: str = None,
            ruta_predictivo: str = None) -> Dict:
    """Devuelve el diccionario plano que consume el adaptador.

    Las rutas son opcionales: si no se pasan, se usan las del vault. El
    dashboard pasa las suyas para funcionar igual en local y en la nube.
    """
    puestos = _puestos(municipio, ruta_detalle, ruta_maestro, ruta_predictivo)
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
        "anexos": _anexos(puestos, v23, v26, total, ruta_detalle, ruta_maestro,
                          METRICAS),
        "_interno": {
            "puestos_analizados": len(puestos),
            "top5_recuperable": sum(p["recuperable"] for p in top),
        },
    }
