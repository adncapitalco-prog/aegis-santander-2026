# -*- coding: utf-8 -*-
"""
RUTAS · resolucion de la raiz del proyecto sin rutas absolutas
==============================================================

PROBLEMA QUE RESUELVE
---------------------
Diez modulos de AEGIS declaraban la raiz como cadena literal:

    RAIZ = r"C:\\Users\\Javier\\Documents\\AEGIS-POLITICA"

En la nube esa ruta no existe. Y como casi todos los usos van envueltos en un
`if os.path.exists(...)`, el fallo no produce error: produce un vacio. Es el
mismo patron que costo tres despliegues con el CSV predictivo.

COMO SE RESUELVE AHORA
----------------------
Se sube por el arbol de directorios desde `__file__` hasta encontrar la marca
del proyecto: un archivo `manifest.json` en la raiz. Sin ruta fija, sin contar
niveles de `parent` —contar niveles es otra forma de hardcodear la
profundidad— y sin depender del directorio de trabajo.

    AEGIS_RAIZ (variable de entorno)   manda, si esta definida
    manifest.json en un ancestro       resolucion normal
    error explicito                    si no se encuentra

ORDEN DE PRIORIDAD
------------------
1. `AEGIS_RAIZ` si esta definida y existe. Sirve para pruebas y para mover el
   vault de sitio sin tocar codigo.
2. El primer ancestro que contenga `manifest.json`.
3. Error. No se devuelve el directorio actual: un `Path.cwd()` silencioso
   hace que el programa funcione o no segun desde donde se lance, y eso es
   peor que fallar.

DEPENDENCIAS
------------
os, pathlib. Nada mas.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

MARCA = "manifest.json"
VARIABLE = "AEGIS_RAIZ"


def raiz_proyecto(desde: Optional[Path] = None, requerir: bool = True) -> Optional[Path]:
    """Directorio que contiene `manifest.json`.

    Parametros
    ----------
    desde    punto de partida; por defecto el archivo que llama
    requerir si es True, lanza RuntimeError cuando no encuentra la raiz

    Devuelve
    --------
    Path de la raiz, o None si `requerir=False` y no se encontro.
    """
    entorno = os.environ.get(VARIABLE)
    if entorno and Path(entorno).is_dir():
        return Path(entorno).resolve()

    inicio = Path(desde).resolve() if desde else Path(__file__).resolve()
    if inicio.is_file():
        inicio = inicio.parent

    for candidato in [inicio] + list(inicio.parents):
        if (candidato / MARCA).is_file():
            return candidato

    if requerir:
        raise RuntimeError(
            "No se encontro la raiz del proyecto: ningun ancestro de %s "
            "contiene %s. Define la variable %s o ejecuta desde dentro del "
            "proyecto." % (inicio, MARCA, VARIABLE))
    return None


def ruta(*partes: str) -> Path:
    """Ruta absoluta a un recurso del proyecto. Falla si no hay raiz."""
    return raiz_proyecto().joinpath(*partes)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    r = raiz_proyecto()
    print("raiz del proyecto: %s" % r)
    print("manifest existe  : %s" % (r / MARCA).is_file())
