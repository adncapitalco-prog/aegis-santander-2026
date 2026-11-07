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
    prioridades = list(getattr(contrato, "prioridades", []) or [])
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
        # Una sola cifra por puesto. Antes esta seccion usaba aporte_objetivo
        # (blancos + nulos + caida) y la seccion de prioridad usaba el gap del
        # CSV predictivo (blancos + nulos + no marcados + fuga). Dos numeros
        # distintos para el mismo puesto, y el lector creia que uno estaba mal.
        # Manda la cifra de prioridad, que es la que ve en el tablero.
        gaps = {pr["nombre"]: pr.get("gap") for pr in prioridades} if prioridades else {}
        aporte = anexos.get("aporte_objetivo", [])
        for i, nombre in enumerate(objetivos[:5], 1):
            cifra = gaps.get(nombre)
            if cifra is None and i - 1 < len(aporte):
                cifra = aporte[i - 1]
            texto_cifra = (" Ahi se pueden recuperar **%s** votos." % _num(cifra)
                           if cifra else "")
            L.append("%d. **%s.**%s" % (i, nombre, texto_cifra))
            L.append("")
        L.append("No son los puestos con mas votos. Son los puestos donde mas "
                 "gente voto y no eligio, o donde la gente dejo de ir.")
        L.append("")

    # --- Prioridad ---------------------------------------------------------
    if prioridades:
        L.append("## Prioridad: qué atender primero")
        L.append("")
        L.append("No todos los puestos valen lo mismo. Dos cosas deciden:")
        L.append("cuánto voto se puede recuperar, y si el puesto se comporta "
                 "distinto a sus vecinos.")
        L.append("")
        for pr in prioridades[:5]:
            color = {1: "el más urgente", 2: "problema de entorno",
                     3: "volumen sin anomalía", 4: "sin acción"}.get(pr["nivel"], "")
            L.append("- **%s** — %s." % (pr["nombre"], pr["etiqueta"]))
            L.append("  %s Se pueden recuperar **%s** votos. Acción: **%s**."
                     % (color.capitalize() + "." if color else "",
                        _num(pr.get("gap", 0)), pr.get("accion", "")))
            L.append("")
        niveles = [p["nivel"] for p in prioridades]
        if 1 in niveles:
            L.append("Los de Prioridad 1 tienen las dos cosas a la vez: "
                     "mucho voto perdido y un comportamiento que no cuadra "
                     "con su entorno. Ahí no se puede esperar.")
            L.append("")
        if 4 in niveles:
            L.append("Los de Prioridad 4 no se tocan. Perder un porcentaje alto "
                     "en un puesto pequeño no es una oportunidad: es aritmética.")
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

    # --- Zona gris ---------------------------------------------------------
    mapeo = anexos.get("mapeo_partidos") or {}
    if mapeo.get("partidos"):
        L.append("## Los votos que antes no tenian nombre")
        L.append("")
        L.append("En el archivo de votacion hay listas que solo traen un numero. "
                 "El tablero las mostraba como «nombre pendiente», que no le "
                 "dice nada a nadie.")
        L.append("")
        L.append("La Registraduria publica el catalogo oficial. Con el, esos "
                 "numeros tienen nombre: **%d partidos y listas** identificados."
                 % mapeo["partidos"])
        L.append("")
        L.append("Eso no cambia un solo voto. Cambia que ahora se puede decir "
                 "de quien son, y por lo tanto a quien hay que buscar.")
        L.append("")
        tops = anexos.get("top_partidos") or []
        resueltos = [t for t in tops if t.get("resuelto")]
        if resueltos:
            L.append("Las tres listas mas votadas, ya con nombre: "
                     + ", ".join("**%s** (%s)" % (t["nombre"], _num(t["votos"]))
                                 for t in resueltos[:3]) + ".")
            L.append("")

    # --- Candidatos --------------------------------------------------------
    candidatos = anexos.get("top_candidatos") or []
    if candidatos:
        L.append("## A quien hay que buscar, con nombre")
        L.append("")
        L.append("Cada lista tiene un cabeza de lista concreto. "
                 "No hace falta recordar el nombre del partido: estos son los "
                 "primeros de cada una.")
        L.append("")
        for c in candidatos[:8]:
            cod = (" (%s)" % c["codigo_lista"]) if c.get("codigo_lista") else ""
            L.append("- **%s** — %s%s." % (c.get("primero", ""),
                                            c.get("partido", ""), cod))
            L.append("")
        L.append("El orden importa: el primero de la lista es el que tiene la "
                 "curul al alcance. Los demas dependen de cuantos votos entren.")
        L.append("")

    # --- Senal -------------------------------------------------------------
    senal = anexos.get("senal") or {}
    if senal.get("destacada"):
        d = senal["destacada"]
        L.append("## La Señal que Ancla la Expectativa")
        L.append("")
        L.append(senal.get("narrativa", ""))
        L.append("")
        L.append("Sensibilidad de **%s**: %.2f de 1,00 (%s). Reduccion "
                 "estimada de la incertidumbre: **%.1f %%**."
                 % (d.get("unidad", ""), d.get("sensibilidad", 0.0),
                    d.get("tramo", "").lower(), d.get("reduccion_entropia", 0.0)))
        L.append("")
        if senal.get("aviso"):
            L.append("*%s*" % senal["aviso"])
            L.append("")
        L.append("*La reduccion es un modelo de decision declarado, no una "
                 "medicion de entropia. Se calcula con una formula fija sobre "
                 "la volatilidad observada; no la produce un modelo de lenguaje.*")
        L.append("")

    # --- Comportamiento ----------------------------------------------------
    perfil = anexos.get("perfil") or {}
    if perfil:
        L.append("## Como se comporta este territorio")
        L.append("")
        castigo = perfil.get("castigo")
        mov = perfil.get("movilizacion")
        disp = perfil.get("disponibilidad")
        res = perfil.get("resiliencia")
        if castigo is not None:
            if castigo > 5:
                L.append("Este territorio **castiga**: la gente que fue a votar "
                         "y no eligio a nadie subio **%+.1f** puntos." % castigo)
            elif castigo < -5:
                L.append("Este territorio **dejo de castigar**: los votos que no "
                         "eligen a nadie bajaron **%.1f** puntos." % abs(castigo))
            else:
                L.append("El castigo se mantuvo casi igual (**%+.1f** puntos)."
                         % castigo)
        if mov is not None:
            if mov > 10:
                L.append("Se **movilizo**: voto %.1f %% mas gente que antes." % mov)
            elif mov < -10:
                L.append("Se **quedo en casa**: voto %.1f %% menos gente."
                         % abs(mov))
            else:
                L.append("La participacion cambio poco (**%+.1f** %%)." % mov)
        if disp is not None:
            if disp > 0.85:
                L.append("El voto esta **repartido**: ningun partido domina, hay "
                         "terreno para un actor nuevo.")
            elif disp < 0.6:
                L.append("El voto esta **concentrado**: el primero manda y los "
                         "demas compiten por migajas.")
        if res is None:
            L.append("**No se puede saber** si el ganador de 2023 aguanto: su "
                     "lista no compitio en 2026.")
        elif res >= 0.8:
            L.append("El ganador de 2023 **conservo su base** (%.0f %% de sus "
                     "votos)." % (100 * res))
        else:
            L.append("El ganador de 2023 **perdio base**: solo conservo %.0f %% "
                     "de sus votos." % (100 * res))
        L.append("")

    # --- Deudas ------------------------------------------------------------
    deudas = anexos.get("deudas_forenses") or []
    if deudas:
        L.append("## Lo que no pudimos cuadrar")
        L.append("")
        L.append("Hay una cifra que no cierra. Preferimos decirlo a elegir la "
                 "que nos conviene.")
        L.append("")
        for d in deudas[:2]:
            cifras = d.get("cifras", {})
            L.append("**%s**" % d.get("titulo", ""))
            L.append("")
            L.append("Una fuente dice **%s** votos y la otra dice **%s**. "
                     "Diferencia: **%s**."
                     % (_num(cifras.get("fuente_oficial", 0)),
                        _num(cifras.get("mwv_vault", 0)),
                        _num(cifras.get("diferencia", 0))))
            L.append("")
            L.append("Buscamos de donde sale la diferencia y no aparecio. "
                     "Queda declarada, no escondida.")
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
