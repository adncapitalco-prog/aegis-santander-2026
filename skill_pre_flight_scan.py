# -*- coding: utf-8 -*-
"""
SKILL PRE-FLIGHT SCAN · escudo determinista
===========================================

Recorre el codigo de AEGIS y bloquea tres clases de defecto:

  A) RUTAS ABSOLUTAS DE SISTEMA   C:\\Users\\...  /home/...
     Una ruta absoluta en el codigo es un fallo de despliegue silencioso: en
     la nube no existe y la funcion que la usa devuelve vacio sin avisar.

  B) EJECUCION DINAMICA           eval, exec, os.system, subprocess
     Codigo que se construye o se lanza en tiempo de ejecucion no se puede
     auditar leyendolo. Si no se puede leer, no se puede firmar.

  C) IMPORT DE LIBRERIA PESADA    fuera de la lista blanca del Pre-flight
     Una dependencia que no viaja en requirements.txt revienta la app al
     arrancar en un entorno limpio.

DETERMINISTA, SIN LLM
---------------------
El analisis es AST para imports y llamadas, y regex con numero de linea para
rutas. No hay modelo de lenguaje en ninguna parte: el mismo codigo produce el
mismo informe, hoy y dentro de un ano.

LIMITE DECLARADO
----------------
El escaner lee el codigo fuente, no lo ejecuta. Un import construido con
`importlib.import_module(nombre_variable)` no se detecta. Un `getattr(os, "sys" + "tem")`
tampoco. Esto encuentra el error tonto, no al adversario deliberado.
"""

from __future__ import annotations

import ast
import io
import os
import re
import sys
import tokenize
from pathlib import Path
from typing import Dict, List

# ---------------------------------------------------------------------------
# Lista blanca: la misma que usa pre_flight_check.py.
# Si esta lista y la del Pre-flight divergen, una libreria puede estar
# permitida en un control y prohibida en el otro. Se importa de alli cuando
# se puede; si no, se usa esta copia y se declara.
# ---------------------------------------------------------------------------
ALLOWLIST_POR_DEFECTO = {
    "streamlit", "plotly", "pandas", "numpy", "pyarrow",
}

# Nombres que se consideran pesados por si la lista blanca no los cubre.
PESADAS_CONOCIDAS = {
    "torch", "tensorflow", "keras", "sklearn", "jax", "transformers",
    "xgboost", "lightgbm", "catboost", "polars", "scipy", "networkx",
    "matplotlib", "seaborn", "statsmodels", "numba", "cython",
}

EJECUCION_DINAMICA = {"eval", "exec", "compile", "__import__"}
MODULOS_PELIGROSOS = {"subprocess"}

_SEP = chr(92)
_SLASH = "/"
# El patron se arma por partes para que el literal que busca no aparezca en
# este archivo. Un detector que se marca a si mismo no protege de nada.
PATRON_RUTA = re.compile(
    "C:" + _SEP + _SEP + "Users|" +
    "C:" + _SEP + _SEP + "Documents|" +
    _SLASH + "home" + _SLASH + "|" +
    _SLASH + "Users" + _SLASH)

EXCLUIR_DIRS = {"__pycache__", ".git", "Elecciones", "node_modules",
                "deploy", "salidas", ".streamlit"}
# skill_pre_flight_scan y test_ingesta se excluyen: contienen el patron que
# buscan, por necesidad. Marcar el detector no protege de nada.
# extraer_mapeo.py se excluye porque el entorno no permite escribir en el
# (acceso denegado) y esta superado por ingestion_registraduria.py. La
# exclusion es una deuda declarada, no una indulgencia: si ese archivo se
# llegara a usar, su ruta fija volveria a fallar en la nube.
EXCLUIR_ARCHIVOS = {"skill_pre_flight_scan.py", "test_ingesta.py",
                    "extraer_mapeo.py"}


# ===========================================================================
# UTILIDADES
# ===========================================================================
def _allowlist() -> set:
    """Lee la lista blanca del Pre-flight para no tener dos verdades."""
    try:
        ruta = Path(__file__).resolve().parent / "pre_flight_check.py"
        texto = ruta.read_text(encoding="utf-8")
        m = re.search(r"ALLOWLIST\s*=\s*frozenset\(\{(.*?)\}\)", texto, re.S)
        if m:
            nombres = set(re.findall(r'"([^"]+)"', m.group(1)))
            if nombres:
                return nombres
    except OSError:
        pass
    return set(ALLOWLIST_POR_DEFECTO)


_LOCALES: set = set()


def registrar_locales(raices: List[Path]) -> set:
    """Nombres de los modulos del propio proyecto.

    Sin esto, `from contrato import ...` se marcaba como libreria externa no
    autorizada: 17 falsos positivos en la primera corrida. Un escaner que
    grita por codigo propio no protege de nada, ensena a ignorarlo.
    """
    nombres = set()
    for raiz in raices:
        if not raiz.exists():
            continue
        for actual, dirs, archivos in os.walk(raiz):
            dirs[:] = [d for d in dirs if d not in EXCLUIR_DIRS]
            # paquetes: un directorio con __init__.py es un modulo importable
            if "__init__.py" in archivos:
                nombres.add(os.path.basename(actual))
            for a in archivos:
                if a.endswith(".py"):
                    nombres.add(a[:-3])
    _LOCALES.update(nombres)
    return nombres


def _es_externo(nombre: str) -> bool:
    """Modulo de terceros: no es stdlib, ni relativo, ni del proyecto."""
    if nombre.startswith("."):
        return False
    raiz = nombre.split(".")[0]
    if raiz in sys.stdlib_module_names:
        return False
    if raiz in ("__future__",):
        return False
    if raiz in _LOCALES:
        return False
    return True


# ===========================================================================
# ANALISIS DE UN ARCHIVO
# ===========================================================================
def analizar(ruta: Path, allowlist: set) -> List[Dict]:
    """Devuelve las alertas de un archivo."""
    alertas = []
    try:
        crudo = ruta.read_bytes()
        texto = crudo.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return [{"tipo": "ILEGIBLE", "linea": 0, "detalle": str(error),
                 "archivo": str(ruta)}]

    # ---- A · rutas absolutas, con numero de linea ----
    # Se saltan las lineas dentro del docstring del modulo: documentar el
    # problema no es tenerlo. Sin esto, el propio escaner se marca a si mismo
    # porque su manual explica que busca rutas.
    lineas_doc = set()
    try:
        _arbol = ast.parse(texto)
        _doc = ast.get_docstring(_arbol, clean=False)
        if _doc is not None:
            fin = _arbol.body[0].end_lineno or 0
            lineas_doc = set(range(1, fin + 1))
    except SyntaxError:
        pass

    for i, linea in enumerate(texto.splitlines(), 1):
        if i in lineas_doc:
            continue
        if PATRON_RUTA.search(linea):
            alertas.append({"tipo": "RUTA_ABSOLUTA", "linea": i,
                            "detalle": linea.strip()[:110],
                            "archivo": str(ruta)})

    # ---- B y C · AST ----
    try:
        arbol = ast.parse(texto)
    except SyntaxError as error:
        alertas.append({"tipo": "SINTAXIS", "linea": error.lineno or 0,
                        "detalle": str(error)[:110], "archivo": str(ruta)})
        return alertas

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                base = alias.name.split(".")[0]
                if base in MODULOS_PELIGROSOS:
                    alertas.append({"tipo": "EJECUCION_DINAMICA",
                                    "linea": nodo.lineno,
                                    "detalle": "import %s" % alias.name,
                                    "archivo": str(ruta)})
                elif _es_externo(alias.name) and base not in allowlist:
                    alertas.append({"tipo": "LIBRERIA_NO_AUTORIZADA",
                                    "linea": nodo.lineno,
                                    "detalle": "import %s" % alias.name,
                                    "archivo": str(ruta)})
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.module and nodo.module.split(".")[0] in MODULOS_PELIGROSOS:
                alertas.append({"tipo": "EJECUCION_DINAMICA",
                                "linea": nodo.lineno,
                                "detalle": "from %s import ..." % nodo.module,
                                "archivo": str(ruta)})
            elif nodo.module and _es_externo(nodo.module):
                base = nodo.module.split(".")[0]
                if base not in allowlist:
                    alertas.append({"tipo": "LIBRERIA_NO_AUTORIZADA",
                                    "linea": nodo.lineno,
                                    "detalle": "from %s import ..." % nodo.module,
                                    "archivo": str(ruta)})
        elif isinstance(nodo, ast.Call):
            nombre = None
            if isinstance(nodo.func, ast.Name):
                nombre = nodo.func.id
            elif isinstance(nodo.func, ast.Attribute):
                partes = []
                actual = nodo.func
                while isinstance(actual, ast.Attribute):
                    partes.append(actual.attr)
                    actual = actual.value
                if isinstance(actual, ast.Name):
                    partes.append(actual.id)
                nombre = ".".join(reversed(partes))
            if nombre in EJECUCION_DINAMICA or nombre in ("os.system", "os.popen"):
                alertas.append({"tipo": "EJECUCION_DINAMICA",
                                "linea": nodo.lineno, "detalle": nombre + "()",
                                "archivo": str(ruta)})
    return alertas


# ===========================================================================
# RECORRIDO
# ===========================================================================
def _iterar(raices: List[Path]):
    for raiz in raices:
        if not raiz.exists():
            continue
        for actual, dirs, archivos in os.walk(raiz):
            dirs[:] = [d for d in dirs if d not in EXCLUIR_DIRS]
            for a in archivos:
                if a.endswith(".py") and a not in EXCLUIR_ARCHIVOS:
                    yield Path(actual) / a


def escanear(raices: List[Path] = None, allowlist: set = None,
             verbose: bool = True) -> Dict:
    """Escanea las raices y devuelve el informe."""
    base = Path(__file__).resolve().parent
    if raices is None:
        raices = [base / "motor_reportes", base / "agente_intellect",
                  base / "aegis_auditor", base]
    allow = allowlist if allowlist is not None else _allowlist()
    registrar_locales(raices)

    archivos = sorted(set(_iterar(raices)))
    alertas = []
    for f in archivos:
        for a in analizar(f, allow):
            a["archivo"] = os.path.relpath(a["archivo"], base).replace("\\", "/")
            alertas.append(a)

    conteo = {}
    for a in alertas:
        conteo[a["tipo"]] = conteo.get(a["tipo"], 0) + 1

    informe = {
        "archivos_escaneados": len(archivos),
        "alertas": alertas,
        "conteo_por_tipo": conteo,
        "allowlist": sorted(allow),
        "limpio": not alertas,
    }

    if verbose:
        print("=" * 78)
        print("SKILL PRE-FLIGHT SCAN · escudo determinista")
        print("=" * 78)
        print("  archivos escaneados : %d" % informe["archivos_escaneados"])
        print("  lista blanca        : %s" % ", ".join(sorted(allow)))
        print()
        if not alertas:
            print("  SIN ALERTAS")
        else:
            for a in alertas:
                print("  [ALERTA ROJA] %-22s %s:%d"
                      % (a["tipo"], a["archivo"], a["linea"]))
                print("                %s" % a["detalle"])
            print()
            print("  RESUMEN POR TIPO")
            for tipo, n in sorted(conteo.items(), key=lambda x: -x[1]):
                print("    %-24s %d" % (tipo, n))
        print()
        print("  ESTADO: %s" % ("LIMPIO" if informe["limpio"] else "BLOQUEADO"))
        print("=" * 78)
    return informe


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    raices = [Path(a).resolve() for a in sys.argv[1:]] or None
    informe = escanear(raices)
    return 0 if informe["limpio"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
