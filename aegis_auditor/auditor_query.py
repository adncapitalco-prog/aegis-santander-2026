# -*- coding: utf-8 -*-
"""
AUDITOR QUERY · consulta de la memoria institucional
====================================================

Lee los registros del Auditor y responde preguntas sobre ellos.

DEPENDENCIAS
------------
json, pathlib, re. Nada mas. Sin pandas, sin numpy, sin streamlit.

POR QUE SIN DEPENDENCIAS
------------------------
Esta es una herramienta de desarrollo que debe poder correr en cualquier
entorno, incluso en uno donde el resto de AEGIS no esta instalado. Un modulo
de consulta que arrastra pandas para leer cuatro archivos de texto no es
ligero: es comodo.

FORMATO QUE ESPERA
------------------
Cada entrada de los .md empieza por "- [" y sigue el formato declarado en
auditor_constitution.md. El parser busca esas lineas; no interpreta la prosa.
Es deliberadamente fragil: si el formato cambia, la consulta devuelve menos
resultados y eso se nota.

SOLO APPEND
-----------
`registrar_bug` y `registrar_leccion` anaden al final. No hay funcion para
borrar ni para reescribir. Si una entrada es equivocada, se anade otra que la
corrija.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

BASE = Path(__file__).resolve().parent

ARCHIVOS = {
    "constitucion": BASE / "auditor_constitution.md",
    "decisiones": BASE / "decision_log.md",
    "bugs": BASE / "bug_registry.md",
    "lecciones": BASE / "lessons_learned.md",
    "manifiesto": BASE / "forensic_manifest.json",
}

ENTRADA = re.compile(r"^-\s*\[(.+?)\]", re.MULTILINE)

# Los registros estan escritos sin tildes por convencion del proyecto, pero
# quien consulta escribe con tildes. Sin normalizar, "metrica" no encuentra
# "métrica" y la memoria parece vacia donde no lo esta.
_ACENTOS = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")


def _normalizar(texto: str) -> str:
    """Minusculas y sin tildes, para que la busqueda no dependa de como se escriba."""
    return str(texto).translate(_ACENTOS).lower().strip()
CAMPOS = re.compile(r"\[([^\]]*)\]")


# ===========================================================================
# LECTURA
# ===========================================================================
def _leer(nombre: str) -> str:
    ruta = ARCHIVOS.get(nombre)
    if ruta is None or not ruta.exists():
        return ""
    try:
        return ruta.read_text(encoding="utf-8")
    except OSError:
        return ""


def _entradas(texto: str) -> List[Dict]:
    """Parte el texto en entradas de la forma '- [campo] [campo] ...'."""
    salida = []
    for linea in texto.splitlines():
        limpia = linea.strip()
        if not limpia.startswith("- ["):
            continue
        campos = CAMPOS.findall(limpia)
        if campos:
            salida.append({"campos": campos, "texto": limpia})
    return salida


# ===========================================================================
# CONSULTAS
# ===========================================================================
def buscar_leccion(keyword: str) -> List[Dict]:
    """Lecciones cuyo texto contenga la palabra, sin distinguir mayusculas."""
    if not keyword or not str(keyword).strip():
        return []
    objetivo = _normalizar(keyword)
    hallazgos = []
    for e in _entradas(_leer("lecciones")):
        if objetivo in _normalizar(e["texto"]):
            hallazgos.append({
                "leccion": e["campos"][0] if e["campos"] else "",
                "contexto": e["campos"][1] if len(e["campos"]) > 1 else "",
                "regla": e["campos"][2] if len(e["campos"]) > 2 else "",
                "texto": e["texto"],
            })
    return hallazgos


def verificar_decision(tema: str) -> List[Dict]:
    """Decisiones tomadas sobre un tema."""
    if not tema or not str(tema).strip():
        return []
    objetivo = _normalizar(tema)
    hallazgos = []
    for e in _entradas(_leer("decisiones")):
        if objetivo in _normalizar(e["texto"]):
            hallazgos.append({
                "fecha": e["campos"][0] if e["campos"] else "",
                "decision": e["campos"][1] if len(e["campos"]) > 1 else "",
                "razon": e["campos"][2] if len(e["campos"]) > 2 else "",
                "alternativas": e["campos"][3] if len(e["campos"]) > 3 else "",
                "superada": "SUPERADA" in e["texto"].upper(),
            })
    return hallazgos


def buscar_bug(keyword: str) -> List[Dict]:
    """Bugs registrados que mencionen la palabra."""
    if not keyword or not str(keyword).strip():
        return []
    objetivo = _normalizar(keyword)
    hallazgos = []
    for e in _entradas(_leer("bugs")):
        if objetivo in _normalizar(e["texto"]):
            hallazgos.append({
                "id": e["campos"][0] if e["campos"] else "",
                "sintoma": e["campos"][1] if len(e["campos"]) > 1 else "",
                "root_cause": e["campos"][2] if len(e["campos"]) > 2 else "",
                "fix": e["campos"][3] if len(e["campos"]) > 3 else "",
                "test_regresion": e["campos"][4] if len(e["campos"]) > 4 else "",
            })
    return hallazgos


def resumen() -> Dict:
    """Cuenta lo que hay registrado. Sirve para el arranque de sesion."""
    return {
        "decisiones": len(_entradas(_leer("decisiones"))),
        "bugs": len(_entradas(_leer("bugs"))),
        "lecciones": len(_entradas(_leer("lecciones"))),
        "deudas_abiertas": len([b for b in _entradas(_leer("bugs"))
                                if "DEUDA" in b["texto"]]),
        "skills_registrados": len(listar_skills()),
    }


def estado_manifiesto() -> Dict:
    """Verifica si los archivos del manifiesto siguen con su hash."""
    import hashlib
    ruta = ARCHIVOS.get("manifiesto")
    if ruta is None or not ruta.exists():
        return {"ok": False, "motivo": "sin manifiesto", "archivos": 0, "problemas": []}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (ValueError, OSError) as error:
        return {"ok": False, "motivo": str(error), "archivos": 0, "problemas": []}

    problemas = []
    entradas = datos.get("archivos", {})
    for rel, esperado in entradas.items():
        p = (BASE.parent.parent / rel) if not Path(rel).is_absolute() else Path(rel)
        if not p.exists():
            problemas.append({"archivo": rel, "motivo": "no existe"})
            continue
        try:
            real = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            problemas.append({"archivo": rel, "motivo": "no se pudo leer"})
            continue
        if real != esperado:
            problemas.append({"archivo": rel, "motivo": "hash distinto"})
    return {"ok": not problemas, "archivos": len(entradas), "problemas": problemas}


# ===========================================================================
# ESCRITURA (solo append)
# ===========================================================================
def _anadir(nombre: str, linea: str) -> bool:
    ruta = ARCHIVOS.get(nombre)
    if ruta is None:
        return False
    try:
        with ruta.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n" + linea.rstrip() + "\n")
        return True
    except OSError:
        return False


def registrar_bug(bug_dict: Dict) -> bool:
    """Anade un bug al registro. Solo append.

    Campos: id, sintoma, root_cause, fix, test_regresion
    """
    requeridos = ("id", "sintoma", "root_cause", "fix", "test_regresion")
    if not isinstance(bug_dict, dict):
        return False
    if any(k not in bug_dict for k in requeridos):
        return False
    linea = "- [%s] [%s] [%s] [%s] [%s]" % tuple(
        str(bug_dict[k]).replace("[", "(").replace("]", ")") for k in requeridos)
    return _anadir("bugs", linea)


def registrar_leccion(leccion: str, contexto: str, regla: str) -> bool:
    """Anade una leccion. Solo append."""
    if not leccion or not regla:
        return False
    limpio = [str(x).replace("[", "(").replace("]", ")") for x in (leccion, contexto, regla)]
    return _anadir("lecciones", "- [%s] [%s] [%s]" % tuple(limpio))




# ===========================================================================
# VERIFICACION DE SKILLS
# ===========================================================================
SKILLS = BASE.parent / "skills_manifest.json"


def verificar_skill(nombre: str) -> bool:
    """True solo si el script esta registrado en skills_manifest.json.

    La lista es la unica forma de distinguir un modulo del sistema de un
    archivo suelto que alguien dejo en la carpeta. Devuelve False tambien si
    el manifiesto falta o esta mal formado: no se puede afirmar que un script
    esta registrado cuando el registro no se puede leer.
    """
    if not nombre or not str(nombre).strip():
        return False
    if not SKILLS.exists():
        return False
    try:
        datos = json.loads(SKILLS.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return False
    skills = datos.get("skills", {})
    clave = str(nombre).strip()
    if clave in skills:
        return True
    # aceptar tambien el nombre de archivo con extension
    limpio = clave[:-3] if clave.endswith(".py") else clave
    return limpio in skills


def listar_skills() -> List[str]:
    """Nombres registrados, ordenados."""
    if not SKILLS.exists():
        return []
    try:
        datos = json.loads(SKILLS.read_text(encoding="utf-8"))
        return sorted(datos.get("skills", {}))
    except (ValueError, OSError):
        return []

# ===========================================================================
# PROTOCOLO DE ARRANQUE
# ===========================================================================
def consultar_al_inicio() -> str:
    """Lo que el DSH debe leer al empezar una sesion nueva."""
    r = resumen()
    m = estado_manifiesto()
    lineas = [
        "AUDITOR AEGIS · estado de la memoria institucional",
        "  decisiones registradas : %d" % r["decisiones"],
        "  bugs registrados       : %d" % r["bugs"],
        "  deudas abiertas        : %d" % r["deudas_abiertas"],
        "  lecciones aprendidas   : %d" % r["lecciones"],
        "  skills registrados     : %d" % r.get("skills_registrados", 0),
        "  manifiesto forense     : %d archivos · %s"
        % (m["archivos"], "integro" if m["ok"] else "CON PROBLEMAS"),
    ]
    for p in m["problemas"][:5]:
        lineas.append("    ! %s: %s" % (p["archivo"], p["motivo"]))
    return "\n".join(lineas)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print(consultar_al_inicio())
    print()
    for palabra in ("Benford", "umbral", "encoding", "grafo"):
        n = len(buscar_leccion(palabra))
        print("  buscar_leccion(%-10r) -> %d" % (palabra, n))
