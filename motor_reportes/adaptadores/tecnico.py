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

    # 2b · PRIORIDAD POR PUESTO
    prioridades = list(getattr(contrato, "prioridades", []) or [])
    if prioridades:
        L += _seccion(3, "Prioridad de intervencion")
        L.append("La prioridad cruza dos senales: voto recuperable absoluto "
                 "(percentil 80) y desviacion ajustada por tamano frente a la "
                 "red de vecinos (percentil 90 del z de la proporcion).")
        L.append("")
        filas = []
        for pr in prioridades:
            filas.append([
                pr.get("nombre", ""),
                "N%d" % pr["nivel"],
                pr.get("etiqueta", ""),
                _num(pr.get("gap", 0)),
                "%+.2f" % float(pr.get("z", 0.0)),
                pr.get("accion", ""),
            ])
        L += _tabla(["Puesto", "Prioridad", "Etiqueta", "Voto recuperable",
                     "Desviacion z", "Accion recomendada"], filas)
        L.append("")
        L.append("**Lectura:** N1 exige ambas condiciones. N3 es volumen sin "
                 "anomalia. N2 es anomalia sin volumen suficiente. N4 no "
                 "requiere accion.")
        # renumerar la seccion siguiente
        metodos_num = 4
    else:
        metodos_num = 3

    # 3 · METODOLOGIA
    if metodos:
        L += _seccion(metodos_num, "Metodologia")
        for m in metodos:
            L.append("- %s" % m)

    # 4 · FUENTES E INTEGRIDAD
    if fuentes:
        L += _seccion(metodos_num + 1, "Fuentes e integridad")
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

    # 4b · MAPEO OFICIAL DE PARTIDOS
    mapeo = a.get("mapeo_partidos") or {}
    if mapeo.get("fuentes"):
        L += _seccion(metodos_num + 1, "Mapeo oficial de partidos")
        L.append("Los codigos de lista del archivo de votacion se resuelven "
                 "contra el archivo oficial de la Registraduria. Sin ese "
                 "mapeo, %d votos del departamento quedarian sin dueno visible."
                 % int(a.get("votos_sin_nombre", 0)))
        L.append("")
        filas = [[f.get("archivo", ""), _num(f.get("bytes", 0)),
                  f.get("encoding", ""), f.get("sha256", "")[:32] + "..."]
                 for f in mapeo["fuentes"]]
        L += _tabla(["Archivo fuente", "Bytes", "Encoding", "SHA256 (32)"], filas)
        L.append("")
        L.append("JSON generado: `%s` · %d partidos · SHA256 `%s...`"
                 % (mapeo.get("archivo", ""), mapeo.get("partidos", 0),
                    mapeo.get("hash", "")[:32]))
        L.append("")

    # 5 · CONTROL DE CALIDAD
    if qa:
        L += _seccion(metodos_num + 3, "Control de calidad")
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
        L += _seccion(metodos_num + 5, "Limites y advertencias")
        L.append("- **El PBC no aplica correccion.** Hay una sola pareja de "
                 "elecciones de distinto tipo (2023 local, 2026 nacional), y con "
                 "una observacion no se estima la varianza del sesgo. Por eso "
                 "las anomalias N1 y N2 se etiquetan con \"incertidumbre alta\": "
                 "se prefiere un rango ancho a un factor inventado.")
        for limite in limites:
            L.append("- %s" % limite)

    # 3b · INDICADORES DE COMPORTAMIENTO
    perfil = a.get("perfil") or {}
    if perfil:
        L += _seccion(metodos_num + 1, "Indicadores de comportamiento electoral")
        L.append("Cinco indicadores del municipio comparado con el propio "
                 "departamento. Ninguno usa categorias culturales: todos salen "
                 "del registro.")
        L.append("")
        formula = {
            "volatilidad": "puestos con partido lider distinto / puestos comparables x 100",
            "castigo": "tasa de perdida 2026 - tasa de perdida 2023 (pp)",
            "movilizacion": "(votos 2026 / votos 2023 - 1) x 100",
            "disponibilidad": "1 - HHI, HHI = suma de cuotas al cuadrado",
            "resiliencia": "votos 2026 del lider de 2023 / votos 2023 de ese partido",
        }
        unidad = {"volatilidad": "%", "castigo": "pp", "movilizacion": "%",
                  "disponibilidad": "0-1", "resiliencia": "0-1"}
        filas = []
        for campo in ("volatilidad", "castigo", "movilizacion",
                      "disponibilidad", "resiliencia"):
            v = perfil.get(campo)
            filas.append([
                campo.capitalize(),
                "NO CALCULABLE" if v is None else ("%.4f" % v),
                unidad[campo],
                formula[campo],
            ])
        L += _tabla(["Indicador", "Valor", "Unidad", "Formula"], filas)
        L.append("")
        L.append("**Volatilidad no sirve para comparar municipios:** los "
                 "universos de partida no se solapan entre una departamental y "
                 "una nacional. Se publica con esa advertencia.")

    # 3c · EXPECTATIVA ESTRATEGICA
    senal = a.get("senal") or {}
    if senal.get("destacada"):
        L += _seccion(metodos_num + 2, "Expectativa estrategica")
        d = senal["destacada"]
        L.append("Indice de sensibilidad por volatilidad historica. **No es una "
                 "propiedad absoluta:** es la posicion de la unidad dentro del "
                 "conjunto. Un 0,80 significa mas sensible que el 80 %% de sus "
                 "pares, no 80 %% de sensibilidad.")
        L.append("")
        L.append("| Unidad | Sensibilidad | Tramo | Es objetivo del reporte |")
        L.append("|---|---:|---|---|")
        for u in senal.get("unidades", []):
            L.append("| %s | %.3f | %s | %s |"
                     % (u["unidad"], u["indice_sensibilidad"], u["tramo"],
                        "si" if u.get("es_objetivo") else ""))
        L.append("")
        L.append("**Senal recomendada para %s: %s (%s).** Reduccion estimada de "
                 "la incertidumbre: %.1f %%."
                 % (d.get("unidad", ""), d.get("senal_evaluada", ""),
                    d.get("senal_nombre", ""), d.get("reduccion_entropia", 0.0)))
        L.append("")
        L.append("| Senal | Nombre | Coste | Reduccion estimada | Recomendada |")
        L.append("|---|---|---|---:|---|")
        for o in senal.get("opciones", []):
            L.append("| %s | %s | %s | %.1f %% | %s |"
                     % (o["senal_evaluada"], o["senal_nombre"], o["coste"],
                        o["reduccion_entropia"],
                        "si" if o["es_la_recomendada"] else ""))
        L.append("")
        L.append("*Modelo:* %s" % senal.get("modelo", ""))
        if senal.get("aviso"):
            L.append("")
            L.append("*%s*" % senal["aviso"])
        L.append("")

    # 6b · DEUDAS FORENSES
    deudas = list(getattr(contrato, "anexos", {}).get("deudas_forenses") or [])
    if deudas:
        L += _seccion(metodos_num + 4, "Deudas forenses abiertas")
        L.append("Una deuda forense es una cifra que el sistema no puede "
                 "resolver con la evidencia disponible. No se elige una cifra "
                 "y se calla la otra: se publican las dos.")
        L.append("")
        for d in deudas:
            cifras = d.get("cifras", {})
            L.append("**%s · %s**" % (d.get("id", ""), d.get("titulo", "")))
            L.append("")
            L.append("- Estado: **%s** · severidad: %s"
                     % (d.get("estado", ""), d.get("severidad", "")))
            L.append("- Cifra A: **%s** · Cifra B: **%s** · diferencia: **%s**"
                     % (_num(cifras.get("fuente_oficial", 0)),
                        _num(cifras.get("mwv_vault", 0)),
                        _num(cifras.get("diferencia", 0))))
            L.append("- Conclusion: %s" % d.get("conclusion", ""))
            fuentes = d.get("fuentes") or []
            if fuentes:
                L.append("")
                L += _tabla(["Fuente", "Aporta", "SHA256 (32)"],
                            [[f.get("nombre", ""), _num(f.get("aporta", 0)),
                              f.get("sha256", "")[:32] + "..."] for f in fuentes])
            verificaciones = d.get("verificaciones_realizadas") or []
            if verificaciones:
                L.append("")
                L.append("Verificaciones realizadas:")
                for v in verificaciones:
                    L.append("- %s" % v)
            L.append("")

    # 7 · REPRODUCIBILIDAD
    L += _seccion(metodos_num + 6, "Reproducibilidad")
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
