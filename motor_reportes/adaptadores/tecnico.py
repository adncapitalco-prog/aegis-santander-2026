# -*- coding: utf-8 -*-
"""
ADAPTADOR · NIVEL TÉCNICO
=========================

Audiencia: directivos, auditores, inversionistas.
Proposito: que la cifra se pueda defender. Metodologia, formula, fuente,
hash, controles y limites.

COMO FUNCIONA
-------------
Este adaptador NO extrae datos ni conoce el dominio. Recibe un ContratoReporte
ya construido y lo reescribe en markdown tecnico.

Los datos de soporte (formula, hashes, QA, limites) vienen en
`contrato.anexos`, que llena la capa de dominio. Si un anexo falta, la seccion
se omite y se declara la ausencia: nunca se rellena con un valor inventado.

REGLA DE AISLAMIENTO
--------------------
Ni un solo nombre propio de dominio en este archivo. Si aparece "Bucaramanga"
o el nombre de un puesto como literal, la separacion de capas fallo.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List

from ..contrato import ContratoReporte

NIVEL = "tecnico"
ESTADO = "operativo"
ETAPA = "5a"

TITULO_NIVEL = "AEGIS TECHNICAL"
ANCHO_TABLA = 78


def describe() -> Dict[str, str]:
    return {"nivel": NIVEL, "estado": ESTADO, "etapa": ETAPA,
            "proposito": "Metodologia, trazabilidad y defensa ante auditoria."}


# =============================================================================
# AYUDANTES DE FORMATO
# =============================================================================
def _num(n) -> str:
    try:
        return format(int(round(float(n))), ",d").replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def _tabla(cabeceras: List[str], filas: List[List[Any]]) -> List[str]:
    lineas = ["| " + " | ".join(cabeceras) + " |",
              "|" + "|".join(["---"] * len(cabeceras)) + "|"]
    for fila in filas:
        celdas = ["" if c is None else str(c) for c in fila]
        lineas.append("| " + " | ".join(celdas) + " |")
    return lineas


def _seccion(numero: int, titulo: str) -> List[str]:
    return ["", "## %d. %s" % (numero, titulo), ""]


# =============================================================================
# RENDERIZADO
# =============================================================================
def desde_contrato(contrato: ContratoReporte) -> str:
    """Convierte un contrato en el informe tecnico completo."""
    a = contrato.anexos or {}
    gap = a.get("gap", {}) or {}
    fuentes = a.get("fuentes", []) or []
    qa = a.get("qa", {}) or {}
    limites = a.get("limites", []) or []
    metodos = a.get("metodos", []) or []

    L: List[str] = []
    L.append("# %s · %s" % (TITULO_NIVEL, contrato.titulo))
    L.append("")
    L.append("**Documento tecnico.** Audiencia: direccion, auditoria, inversionistas.")
    L.append("")
    L.append("Generado: %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    if contrato.metadatos:
        L.append("")
        L.append("| Campo | Valor |")
        L.append("|---|---|")
        for clave, valor in contrato.metadatos.items():
            if clave == "nivel":
                valor = NIVEL
            L.append("| %s | %s |" % (clave, valor))

    # 1 · RESULTADO
    L += _seccion(1, "Resultado")
    if gap:
        punto = gap.get("brecha")
        piso = gap.get("piso")
        techo = gap.get("techo")
        if punto is not None:
            L.append("La brecha estimada es de **%s**." % _num(punto))
        elif piso is not None and techo is not None:
            L.append("La brecha estimada esta entre **%s** y **%s**."
                     % (_num(piso), _num(techo)))
            L.append("")
            L.append("Se publica un rango y no un numero unico porque hay "
                     "componentes sin accesibilidad medida. Un punto seria una "
                     "precision que los datos no sostienen.")
        else:
            L.append("Sin cifra calculable.")
        L.append("")
        if gap.get("incertidumbre"):
            L.append("- Incertidumbre declarada: **%s**" % gap["incertidumbre"])
        if gap.get("confianza"):
            L.append("- Confianza del calculo: **%s**" % gap["confianza"])
        if gap.get("formula"):
            L.append("")
            L.append("Formula aplicada:")
            L.append("")
            L.append("```")
            L.append(gap["formula"])
            L.append("```")
    else:
        L.append("Sin anexo de calculo. **No se reporta cifra**: un numero sin "
                 "metodo no es un resultado, es una afirmacion.")

    # 2 · DESCOMPOSICION
    componentes = gap.get("componentes") or []
    if componentes:
        L += _seccion(2, "Descomposicion de la brecha")
        filas = []
        for c in componentes:
            acc = c.get("accesibilidad")
            filas.append([
                c.get("nombre", ""),
                _num(c.get("monto", 0)),
                "desconocida" if acc is None else ("%.3f" % acc),
                _num(c.get("aporte_piso", 0)),
                _num(c.get("aporte_techo", 0)),
                c.get("fuente", ""),
            ])
        L += _tabla(
            ["Componente", "Monto", "Accesibilidad", "Aporte piso", "Aporte techo", "Fuente"],
            filas)
        L.append("")
        L.append("**Lectura:** una accesibilidad desconocida obliga a publicar un "
                 "rango. El piso es lo que se puede prometer; el techo, lo que se "
                 "podria capturar si todo funcionara.")

    # 3 · METODOLOGIA
    if metodos:
        L += _seccion(3, "Metodologia")
        for m in metodos:
            L.append("- %s" % m)

    # 4 · FUENTES E INTEGRIDAD
    if fuentes:
        L += _seccion(4, "Fuentes e integridad")
        filas = []
        for f in fuentes:
            filas.append([
                f.get("nombre", ""),
                _num(f.get("filas", 0)) if f.get("filas") else "",
                f.get("hash", "")[:32] + "..." if f.get("hash") else "sin hash",
            ])
        L += _tabla(["Fuente", "Filas", "SHA256 (primeros 32)"], filas)
        L.append("")
        L.append("**Regla:** una fuente sin hash declarado se trata como no "
                 "confiable. La ausencia de evidencia es un fallo, no un permiso.")

    # 5 · CONTROL DE CALIDAD
    if qa:
        L += _seccion(5, "Control de calidad")
        controles = qa.get("controles") or []
        if controles:
            L += _tabla(["Control", "Resultado", "Detalle"],
                        [[c.get("nombre", ""), c.get("resultado", ""),
                          c.get("detalle", "")] for c in controles])
        if qa.get("veredicto"):
            L.append("")
            L.append("**Veredicto QA:** %s" % qa["veredicto"])

    # 6 · LIMITES
    if limites:
        L += _seccion(6, "Limites y advertencias")
        for limite in limites:
            L.append("- %s" % limite)

    # 7 · REPRODUCIBILIDAD
    L += _seccion(7, "Reproducibilidad")
    L.append("Para reconstruir este informe:")
    L.append("")
    L.append("```")
    L.append("python 06_Herramientas/pre_flight_check.py --modo deploy")
    L.append("python -m motor_reportes.test_motor_reportes")
    L.append("```")
    L.append("")
    L.append("El Pre-flight verifica hash de fuentes y lista blanca de librerias "
             "antes de cualquier calculo. Si falla, no hay informe.")

    if contrato.pie:
        L.append("")
        L.append("---")
        L.append("")
        L.append(contrato.pie)

    return "\n".join(L).strip() + "\n"


# =============================================================================
# ATAJO
# =============================================================================
def construir(contrato: ContratoReporte) -> str:
    """Alias de `desde_contrato`. Existe para que los tres niveles se llamen igual."""
    return desde_contrato(contrato)
