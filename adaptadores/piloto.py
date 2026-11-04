# -*- coding: utf-8 -*-
"""
ADAPTADOR · NIVEL PILOTO
========================

Traduce datos de un dominio a un ContratoReporte en formato R-01 estricto:
ASD-STE100 en espanol, una idea por linea, cero jerga tecnica.

Este adaptador es el que ya estaba validado. La unica diferencia con la
version anterior es que ahora no genera SVG ni texto: entrega el contrato y
el renderizador hace el resto.

La logica de extraccion vive en `datos_electorales.py`, para que este archivo
solo contenga la REDACCION. Si se cambia el estilo del texto, se cambia aqui
y nada mas.
"""

from __future__ import annotations

from typing import Dict, List

from ..contrato import ContratoReporte, bloque, nodo


def numero(n) -> str:
    """Separador de miles con punto."""
    try:
        return format(int(round(float(n))), ",d").replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def construir(datos: Dict) -> ContratoReporte:
    """Construye el contrato piloto a partir de los datos del dominio.

    `datos` debe traer, como minimo:
        titulo, subtitulo
        v23_total, v26_total, recuperable_total
        top_puestos: lista de dicts con 'nombre' y 'recuperable'
        accion: frase de accion
        pie (opcional)
    """
    top = datos["top_puestos"][:5]
    recuperable_top = sum(p["recuperable"] for p in top)
    ordenes = ["Uno", "Dos", "Tres", "Cuatro", "Cinco"]

    nodos = [
        nodo(numero(datos["v23_total"]) + " votos",
             ["eligieron alcalde en 2023"], "entrada"),
        nodo(numero(datos["v26_total"]) + " votos",
             ["votaron al Senado en 2026"], "entrada"),
        nodo(numero(datos["recuperable_total"]),
             ["votos no llegan a nadie",
              "blanco, nulo o se quedan en casa"], "perdida"),
        nodo("%d puestos" % len(top),
             ["donde se puede pelear mas voto"], "objetivo"),
        nodo(numero(recuperable_top) + " votos",
             ["estan en esos %d puestos" % len(top)], "objetivo"),
        nodo(datos.get("horizonte", "2027"),
             ["aqui se gana o se pierde", "la eleccion"], "objetivo"),
        nodo(datos["accion"], [datos.get("accion_detalle", "")], "accion"),
    ]
    # El nodo de accion no lleva detalle vacio.
    if not nodos[-1].detalle or not nodos[-1].detalle[0]:
        nodos[-1] = nodo(datos["accion"], [], "accion")

    conexiones = [
        (0, 1),   # 2023 -> 2026
        (1, 2),   # 2026 -> brecha
        (2, 5),   # brecha -> horizonte
        (0, 3),   # 2023 -> puestos
        (3, 4),   # puestos -> votos en juego
        (4, 5),   # votos -> horizonte
        (3, 6),   # puestos -> accion
    ]

    bloques: List = [
        bloque("", [
            "La gente si vota en %s." % datos.get("lugar", ""),
            "En 2023 votaron %s personas para %s." % (numero(datos["v23_total"]),
                                                   datos.get("cargo_a", "el cargo local")),
            "En 2026 votaron %s para %s." % (numero(datos["v26_total"]),
                                                datos.get("cargo_b", "el cargo nacional")),
            "Votaron mas, no menos.",
        ]),
        bloque("", [
            "Pero %s votos no llegan a ningun candidato." % numero(datos["recuperable_total"]),
            "Unos son votos en blanco.",
            "Otros son votos nulos.",
            "El resto son barrios donde la gente voto en 2023 y no volvio en 2026.",
        ]),
        bloque("", [
            "Ese voto esta enojado o confundido.",
            "No esta convencido por nadie.",
            "Se puede recuperar.",
        ]),
        bloque("", [
            "Revisa los cinco puestos con mas voto perdido.",
        ]),
        bloque("", ["%s. %s." % (ordenes[i], p["nombre"]) for i, p in enumerate(top)]),
        bloque("", [
            "En esos cinco puestos hay %s votos en juego." % numero(recuperable_top),
            "Es casi la cuarta parte de todo lo que se pierde.",
        ]),
        bloque("", [
            "Haz esto la proxima semana:",
        ]),
        bloque("", [
            "Uno. Visita los cinco puestos.",
            "Dos. Asigna dos delegados a cada uno.",
            "Tres. Habla con quien voto en 2023 y no en 2026.",
        ]),
        bloque("", [
            "Lleva el mensaje del barrio, no el de la ciudad.",
            "Esa gente ya sabe votar.",
            "Solo necesita una razon para volver.",
        ]),
    ]

    # Los objetivos concretos viajan en el contrato. El renderizador los
    # dibuja sin saber que son puestos, valvulas o cuentas.
    objetivos = [p.get("nombre_corto") or p["nombre"]
                 for p in datos["top_puestos"][:8]]

    return ContratoReporte(
        titulo=datos["titulo"],
        subtitulo=datos.get("subtitulo", "Cada numero es un voto que se puede recuperar"),
        nodos=nodos,
        conexiones=conexiones,
        accion=datos["accion"],
        puestos_objetivo=objetivos,
        bloques=bloques,
        pie=datos.get("pie", ""),
        anexos=datos.get("anexos", {}),
        metadatos={
            "nivel": "piloto",
            "norma": "ASD-STE100 es",
            "estilo": "DEGRAU 2",
        },
    )
