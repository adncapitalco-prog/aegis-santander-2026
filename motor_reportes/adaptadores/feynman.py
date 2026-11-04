# -*- coding: utf-8 -*-
"""
ADAPTADOR · NIVEL FEYNMAN
=========================

Audiencia: gerentes de campana, estrategas, cualquier persona que no pidio
el analisis pero tiene que actuar.

Proposito: contar la historia que hay detras de las cifras. Analogia primero,
numero despues, accion al final.

COMO FUNCIONA
-------------
Igual que el nivel tecnico: recibe un ContratoReporte y lo reescribe. No
extrae datos, no conoce el dominio, no tiene nombres propios en el codigo.

Toma del contrato los nodos, los objetivos y los bloques de texto. Los
objetivos los explica uno por uno con la cifra que el propio contrato trae,
sin saber que representan.

REGLA DE ORO
------------
Cada metrica se explica con una frase que un nino entenderia. Ninguna sigla.
Ninguna formula. Si una frase necesita una definicion, se reescribe la frase.

Extension: dos paginas como maximo.
"""

from __future__ import annotations

from typing import Dict, List

from ..contrato import ContratoReporte

NIVEL = "feynman"
ESTADO = "operativo"
ETAPA = "5b"

TITULO_NIVEL = "AEGIS FEYNMAN"
MAX_PAGINAS = 2


def describe() -> Dict[str, str]:
    return {"nivel": NIVEL, "estado": ESTADO, "etapa": ETAPA,
            "proposito": "Explicar el hallazgo a alguien sin contexto previo."}


# =============================================================================
# AYUDANTES
# =============================================================================
def _num(n) -> str:
    try:
        return format(int(round(float(n))), ",d").replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def _de_cada_cien(parte, total) -> str:
    """Convierte una proporcion en 'N de cada 100'. Sin porcentajes."""
    try:
        parte, total = float(parte), float(total)
        if total <= 0:
            return ""
        porcion = round(100.0 * parte / total)
        if porcion <= 0:
            return "menos de 1 de cada 100"
        return "%d de cada 100" % porcion
    except (TypeError, ValueError):
        return ""


def _analogia(contrato: ContratoReporte) -> str:
    """Construye la analogia inicial.

    Usa las cifras crudas de los anexos si estan; si no, cae a los titulos de
    nodo. No nombra el dominio: "el barrio" sirve para cualquier tema.
    """
    cifras = (contrato.anexos or {}).get("cifras") or {}
    nodos = contrato.nodos
    if cifras:
        antes = _num(cifras.get("antes", 0))
        despues = _num(cifras.get("despues", 0))
        perdido = _num(cifras.get("perdido", 0))
    elif len(nodos) >= 3:
        antes, despues, perdido = nodos[0].titulo, nodos[1].titulo, nodos[2].titulo
    else:
        return ""
    return ("Imagina un barrio donde un ano van a votar %s vecinos. "
            "Al ano siguiente van %s. Casi los mismos. "
            "Pero %s de esos votos se van sin elegir a nadie: la persona entro, "
            "marco, y su papel no sirvio."
            % (antes, despues, perdido))


# =============================================================================
# RENDERIZADO
# =============================================================================
def desde_contrato(contrato: ContratoReporte) -> str:
    """Convierte un contrato en un texto narrativo de maximo dos paginas."""
    nodos = contrato.nodos
    objetivos = list(getattr(contrato, "puestos_objetivo", []))
    anexos = contrato.anexos or {}

    L: List[str] = []
    L.append("# %s" % contrato.titulo)
    L.append("")

    # --- Que paso ---------------------------------------------------------
    L.append("## Que paso")
    L.append("")
    analogia = _analogia(contrato)
    if analogia:
        L.append(analogia)
        L.append("")
    for nodo in nodos[:3]:
        if nodo.rol == "accion":
            continue
        # Cada linea de detalle empieza en mayuscula: al unirlas con punto,
        # la segunda quedaba en minuscula despues del punto.
        partes = [d.strip() for d in nodo.detalle if d.strip()]
        detalle = ". ".join(p[0].upper() + p[1:] if p else p for p in partes)
        if detalle:
            detalle += "."
        L.append("- **%s.** %s" % (nodo.titulo, detalle))
    L.append("")

    # --- Que significa ----------------------------------------------------
    L.append("## Que significa esa cifra")
    L.append("")
    if len(nodos) >= 3:
        L.append("Los **%s** no son gente que no fue a votar." % nodos[2].titulo)
        L.append("Son gente que fue, entro al puesto y salio sin marcar a nadie.")
        L.append("")
        L.append("Es distinto. Al que no va hay que convencerlo de ir.")
        L.append("Al que fue y no marco solo hay que darle una razon.")
        L.append("")
    tasa = anexos.get("tasa_perdida")
    if tasa is not None:
        proporcion = _de_cada_cien(tasa, 100)
        L.append("La **tasa de perdida** mide eso: %s personas que fueron a "
                 "votar se fueron sin elegir a nadie." % proporcion)
        L.append("")

    # --- Los objetivos, explicados ---------------------------------------
    if objetivos:
        L.append("## Donde esta el voto, uno por uno")
        L.append("")
        for i, nombre in enumerate(objetivos[:5], 1):
            aporte = anexos.get("aporte_objetivo", [])
            cifra = ""
            if i - 1 < len(aporte):
                cifra = " Ahi se pueden recuperar **%s** votos." % _num(aporte[i - 1])
            L.append("%d. **%s.**%s" % (i, nombre, cifra))
            L.append("")
        L.append("No son los puestos con mas votos. Son los puestos donde mas "
                 "gente voto y no eligio, o donde la gente dejo de ir.")
        L.append("")

    # --- Por que juntos ---------------------------------------------------
    if objetivos:
        L.append("## Por que estos y no otros")
        L.append("")
        L.append("Podrias repartir los delegados por toda la ciudad.")
        L.append("Seria mas comodo de explicar y mucho menos efectivo.")
        L.append("")
        L.append("Los cinco concentran casi una cuarta parte de todo el voto "
                 "perdido. Poner gente donde no se pierde nada es gastar sin "
                 "mover el resultado.")
        L.append("")

    # --- La accion --------------------------------------------------------
    L.append("## Que hacer esta semana")
    L.append("")
    L.append("**%s**" % contrato.accion)
    L.append("")
    for bloque in contrato.bloques:
        if any(palabra in linea.lower()
               for linea in bloque.lineas
               for palabra in ("visita", "asigna", "habla", "haz esto")):
            for linea in bloque.lineas:
                if linea.strip():
                    L.append("- %s" % linea)
    L.append("")
    L.append("No hace falta una caravana. Hace falta que alguien toque la puerta "
             "correcta.")
    L.append("")

    # --- Cierre -----------------------------------------------------------
    if anexos.get("cierre"):
        L.append("## Una ultima cosa")
        L.append("")
        L.append(str(anexos["cierre"]))
        L.append("")

    if contrato.pie:
        L.append("---")
        L.append("")
        L.append(contrato.pie)

    return "\n".join(L).strip() + "\n"


def construir(contrato: ContratoReporte) -> str:
    """Alias de `desde_contrato`."""
    return desde_contrato(contrato)
