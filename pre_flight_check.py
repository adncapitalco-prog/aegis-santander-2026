#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PRE-FLIGHT CHECK · AEGIS-POLITICA
=================================

Guardian fail-closed. Se ejecuta ANTES de cargar cualquier dato o libreria
del sistema. Si algo no cuadra, detiene la ejecucion.

QUE VERIFICA
------------
  1. INTEGRIDAD   cada fuente de datos contra el hash declarado en
                  manifest.json. Un archivo sin hash declarado es un fallo,
                  no un permiso (fail-closed).
  2. LIBRERIAS    requirements.txt contra una lista negra y una lista blanca.
                  Una libreria de la lista negra detiene el proceso.
  3. ESQUEMA      schema_contrato.json, si existe. Aqui solo se valida que
                  sea JSON valido y que declare las columnas sensibles.
                  El enmascaramiento se implementa en la Etapa 2.

CODIGOS DE SALIDA
-----------------
  0  todo correcto
  2  error de uso (argumentos, archivos de configuracion ausentes)
  3  integridad de datos comprometida
  4  libreria no autorizada
  5  contrato de esquema invalido

USO
---
  python 06_Herramientas/pre_flight_check.py --modo deploy
  python 06_Herramientas/pre_flight_check.py --modo dev --verbose

POR QUE NO USA DEPENDENCIAS EXTERNAS
------------------------------------
Este script corre antes de que el sistema cargue nada. Si importara pandas
o pyarrow, estaria haciendo exactamente lo que debe impedir: confiar en el
entorno antes de verificarlo. Solo libreria estandar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

# =============================================================================
# CONTRATO DE SEGURIDAD
# =============================================================================
BLOCKLIST = frozenset({
    "torch", "torchaudio", "torchvision",
    "transformers", "tensorflow", "keras", "spacy",
})

# Permitidas para la dimension POLITICA. En modo deploy, cualquier cosa
# fuera de esta lista es un fallo.
ALLOWLIST = frozenset({
    "streamlit", "plotly", "pandas", "numpy", "pyarrow",
})

# Utilidades que no son dependencias de producto y no deben bloquear.
INOCUAS = frozenset({
    "pytest", "black", "flake8", "mypy", "ruff",
    "setuptools", "wheel", "pip",
})

EXIT_OK = 0
EXIT_USO = 2
EXIT_INTEGRIDAD = 3
EXIT_LIBRERIA = 4
EXIT_ESQUEMA = 5

# La consola de Windows en cp1252 no puede escribir el emoji y el script
# moria con exit 1 en vez de 4. El marcador se degrada si no hay soporte.
try:
    ROJO = "\U0001F534"
    ROJO.encode(sys.stdout.encoding or "ascii")
except (UnicodeEncodeError, LookupError):
    ROJO = "[ERROR]"


# =============================================================================
# UTILIDADES
# =============================================================================
def _configurar_salida():
    """Evita que un caracter no representable tumbe el chequeo.

    Un guardian que muere con exit 1 por un emoji no esta protegiendo nada:
    cambia el codigo de salida y el llamador no distingue un bloqueo de un
    error de programa.
    """
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def raiz_proyecto() -> str:
    """Dos niveles arriba de este archivo: 06_Herramientas/pre_flight_check.py."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha256_archivo(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def cargar_json(ruta: str):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def normalizar_paquete(linea: str) -> str:
    """De 'streamlit==1.66.1' o 'torch>=2.0; extra' saca 'torch'."""
    limpio = linea.split("#", 1)[0].strip()
    if not limpio or limpio.startswith("-"):
        return ""
    for separador in ("==", ">=", "<=", "~=", "!=", ">", "<", "[", ";", " "):
        limpio = limpio.split(separador, 1)[0]
    return limpio.strip().lower()


# =============================================================================
# VERIFICACION 1 · INTEGRIDAD
# =============================================================================
def verificar_integridad(raiz: str, manifiesto: str, verbose: bool) -> int:
    if not os.path.exists(manifiesto):
        print("%s ERROR CRITICO: no existe el manifiesto: %s" % (ROJO, manifiesto))
        print("   Sin manifiesto no hay forma de saber si los datos son los correctos.")
        return EXIT_USO

    try:
        datos = cargar_json(manifiesto)
    except json.JSONDecodeError as error:
        print("%s ERROR CRITICO: manifiesto ilegible (%s)" % (ROJO, error))
        return EXIT_ESQUEMA

    fuentes = datos.get("fuentes", {})
    if not fuentes:
        print("%s ERROR CRITICO: el manifiesto no declara fuentes" % ROJO)
        return EXIT_USO

    print("  Integridad: %d fuente(s) declarada(s)" % len(fuentes))
    fallos = []

    for nombre, esperado in sorted(fuentes.items()):
        ruta = os.path.join(raiz, nombre)
        if not os.path.exists(ruta):
            fallos.append((nombre, "archivo ausente", esperado))
            continue
        real = sha256_archivo(ruta)
        if real != esperado:
            fallos.append((nombre, "hash distinto", esperado, real))
        elif verbose:
            print("     OK  %-44s %s..." % (nombre, real[:16]))

    if fallos:
        print()
        print("%s ERROR CRITICO: Integridad de datos comprometida. Abortando." % ROJO)
        for f in fallos:
            if f[1] == "archivo ausente":
                print("     %-44s ARCHIVO AUSENTE" % f[0])
            elif f[1] == "hash distinto":
                print("     %-44s" % f[0])
                print("        esperado: %s" % f[2])
                print("        real    : %s" % f[3])
            else:
                print("     %-44s %s" % (f[0], f[1]))
        return EXIT_INTEGRIDAD

    print("     todas las fuentes coinciden con el manifiesto")
    return EXIT_OK


# =============================================================================
# VERIFICACION 2 · LIBRERIAS
# =============================================================================
def verificar_librerias(raiz: str, modo: str, verbose: bool) -> int:
    candidatos = [
        os.path.join(raiz, "06_Herramientas", "agente_intellect", "salidas",
                     "requirements.txt"),
        os.path.join(raiz, "06_Herramientas", "agente_intellect", "deploy",
                     "requirements.txt"),
        os.path.join(raiz, "requirements.txt"),
    ]
    ruta = next((c for c in candidatos if os.path.exists(c)), None)
    if ruta is None:
        print("%s ERROR CRITICO: no se encontro requirements.txt" % ROJO)
        print("   Buscado en: %s" % " | ".join(candidatos))
        return EXIT_USO

    with open(ruta, encoding="utf-8") as fh:
        lineas = fh.read().splitlines()

    paquetes = [normalizar_paquete(l) for l in lineas]
    paquetes = [p for p in paquetes if p]

    print("  Librerias: %d declarada(s) en %s"
          % (len(paquetes), os.path.relpath(ruta, raiz)))

    bloqueadas = [p for p in paquetes if p in BLOCKLIST]
    if bloqueadas:
        print()
        for nombre in bloqueadas:
            print("%s ERROR CRITICO: Libreria no autorizada detectada [%s]. Abortando."
                  % (ROJO, nombre))
        print("     La lista negra existe porque estas librerias arrastran modelos")
        print("     pesados y dependencias que el sistema no puede auditar.")
        return EXIT_LIBRERIA

    if modo == "deploy":
        fuera = [p for p in paquetes if p not in ALLOWLIST and p not in INOCUAS]
        if fuera:
            print()
            print("%s ERROR CRITICO: libreria fuera de la lista blanca: %s"
                  % (ROJO, ", ".join(fuera)))
            print("     Modo deploy es estricto. Autorizadas: %s"
                  % ", ".join(sorted(ALLOWLIST)))
            return EXIT_LIBRERIA
        if verbose:
            for p in paquetes:
                print("     OK  %-24s %s" % (p, "allowlist" if p in ALLOWLIST else "inocua"))
    else:
        if verbose:
            for p in paquetes:
                estado = "allowlist" if p in ALLOWLIST else (
                    "inocua" if p in INOCUAS else "fuera de allowlist (permitida en dev)")
                print("     OK  %-24s %s" % (p, estado))

    print("     ninguna libreria de la lista negra")
    return EXIT_OK


# =============================================================================
# VERIFICACION 3 · CONTRATO DE ESQUEMA
# =============================================================================
def verificar_esquema(raiz: str, verbose: bool) -> int:
    rutas = [
        os.path.join(raiz, "schema_contrato.json"),
        os.path.join(raiz, "06_Herramientas", "agente_intellect", "salidas",
                     "schema_contrato.json"),
    ]
    ruta = next((c for c in rutas if os.path.exists(c)), None)
    if ruta is None:
        print("  Esquema: sin contrato declarado (opcional en esta etapa)")
        return EXIT_OK

    try:
        contrato = cargar_json(ruta)
    except json.JSONDecodeError as error:
        print("%s ERROR CRITICO: contrato de esquema invalido (%s)" % (ROJO, error))
        return EXIT_ESQUEMA

    if not isinstance(contrato, dict):
        print("%s ERROR CRITICO: el contrato debe ser un objeto JSON" % ROJO)
        return EXIT_ESQUEMA

    sensibles = []
    for fuente, spec in contrato.items():
        if not isinstance(spec, dict):
            print("%s ERROR CRITICO: '%s' no declara un objeto de columnas" % (ROJO, fuente))
            return EXIT_ESQUEMA
        for columna, meta in spec.items():
            if isinstance(meta, dict) and meta.get("sensible") is True:
                sensibles.append("%s.%s" % (fuente, columna))

    print("  Esquema: contrato valido (%d columna(s) sensible(s) declarada(s))"
          % len(sensibles))
    if verbose:
        for s in sensibles:
            print("     SENSIBLE  %s" % s)
    if sensibles:
        print("     el enmascaramiento se aplica en la Etapa 2")
    return EXIT_OK




# =============================================================================
# VERIFICACION 4 · GOBERNANZA (escudo determinista)
# =============================================================================
def verificar_gobernanza(raiz: str, verbose: bool = False) -> int:
    """Corre el escaner sobre el codigo y bloquea si hay defectos.

    Fail-closed: si el escaner no se puede cargar, es un fallo y no un aviso.
    Un guardia que se ausenta en silencio es peor que uno que no existe,
    porque el que no existe se nota.
    """
    print()
    print("VERIFICACION 4 · GOBERNANZA (escudo determinista)")
    print("-" * 68)

    try:
        import importlib
        escaner = importlib.import_module("skill_pre_flight_scan")
    except ImportError:
        # el paquete de despliegue lo lleva junto al guardian
        candidato = os.path.join(raiz, "skill_pre_flight_scan.py")
        if not os.path.isfile(candidato):
            print("  [%s] escaner de gobernanza AUSENTE" % "ERROR")
            print("  skill_pre_flight_scan.py debe viajar con el guardian.")
            return EXIT_INTEGRIDAD
        sys.path.insert(0, raiz)
        try:
            import importlib
            escaner = importlib.import_module("skill_pre_flight_scan")
        except ImportError as error:
            print("  [%s] escaner ilegible: %s" % ("ERROR", error))
            return EXIT_INTEGRIDAD

    from pathlib import Path
    # El codigo del producto vive en 06_Herramientas/ dentro del vault y en la
    # raiz dentro del paquete de despliegue. Escanear la raiz del vault metia
    # scripts exploratorios heredados (generar_mapa.py, con folium y rutas
    # fijas) en el mismo control que el codigo que si se despliega.
    candidato = Path(raiz) / "06_Herramientas"
    base_codigo = candidato if (candidato / "motor_reportes").is_dir() else Path(raiz)
    raices = [base_codigo]
    for sub in ("motor_reportes", "agente_intellect", "aegis_auditor"):
        d = base_codigo / sub
        if d.is_dir():
            raices.append(d)

    informe = escaner.escanear(raices, verbose=False)
    if informe["limpio"]:
        print("  [%s] %d archivos · sin rutas absolutas, sin eval, "
              "sin librerias no autorizadas" % ("OK", informe["archivos_escaneados"]))
        return EXIT_OK

    print("  [%s] %d defectos en %d archivos"
          % ("ERROR", len(informe["alertas"]), informe["archivos_escaneados"]))
    for alerta in informe["alertas"]:
        print("    %s linea %d · %s" % (alerta["archivo"], alerta["linea"], alerta["tipo"]))
        print("      %s" % alerta["detalle"])
    print()
    print("  El codigo no puede desplegarse con rutas absolutas, ejecucion")
    print("  dinamica ni librerias fuera de la lista blanca.")
    return EXIT_INTEGRIDAD


# =============================================================================
# MAIN
# =============================================================================
def main(argv=None) -> int:
    _configurar_salida()
    parser = argparse.ArgumentParser(
        prog="pre_flight_check",
        description="Guardián fail-closed de AEGIS-POLITICA. "
                    "Verifica integridad, librerías y esquema antes de cargar nada.",
    )
    parser.add_argument("--modo", choices=("deploy", "dev"), default="deploy",
                        help="deploy: estricto (allowlist). dev: solo blocklist.")
    parser.add_argument("--manifest", default=None,
                        help="Ruta al manifest.json. Por defecto en la raíz.")
    parser.add_argument("--verbose", action="store_true", help="Detalle por archivo.")
    parser.add_argument("--raiz", default=None,
                        help="Raiz del proyecto. Por defecto, dos niveles sobre este archivo. "
                             "Se usa cuando el guardian viaja dentro del paquete deploy/.")
    args = parser.parse_args(argv)

    raiz = os.path.abspath(args.raiz) if args.raiz else raiz_proyecto()
    manifiesto = args.manifest or os.path.join(raiz, "manifest.json")

    print("=" * 68)
    print("PRE-FLIGHT CHECK · AEGIS-POLITICA")
    print("  modo      : %s" % args.modo)
    print("  raiz      : %s" % raiz)
    print("=" * 68)

    codigo = verificar_integridad(raiz, manifiesto, args.verbose)
    if codigo != EXIT_OK:
        return codigo

    codigo = verificar_librerias(raiz, args.modo, args.verbose)
    if codigo != EXIT_OK:
        return codigo

    codigo = verificar_esquema(raiz, args.verbose)
    if codigo != EXIT_OK:
        return codigo

    codigo = verificar_gobernanza(raiz, args.verbose)
    if codigo != EXIT_OK:
        return codigo

    print("-" * 68)
    print("PRE-FLIGHT OK · el sistema puede arrancar")
    print("=" * 68)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
