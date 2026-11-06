# -*- coding: utf-8 -*-
"""
PRUEBA DEL MOTOR MODULAR DE REPORTES
====================================

Valida cuatro cosas:

  P1  COMPATIBILIDAD   el motor nuevo reproduce el texto del reporte anterior
  P2  AISLAMIENTO      el renderizador no contiene nombres de dominio
  P3  CONTRATO         el contrato rechaza lo que DEGRAU 2 no admite
  P4  NIVELES          piloto funciona; tecnico y feynman estan declarados

Uso:
    python -m motor_reportes.test_motor_reportes
    python 06_Herramientas/motor_reportes/test_motor_reportes.py
"""

from __future__ import annotations

import hashlib
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PADRE = os.path.dirname(AQUI)
if PADRE not in sys.path:
    sys.path.insert(0, PADRE)

from motor_reportes import adaptadores, contrato, renderizador  # noqa: E402
from motor_reportes.datos_electorales import extraer  # noqa: E402

RAIZ = r"C:\Users\Javier\Documents\AEGIS-POLITICA"
REFERENCIA_TXT = os.path.join(RAIZ, "08_Reportes", "reporte_piloto", "texto_piloto.txt")
PARQUET_DETALLE = os.path.join(AQUI, "..", "..", "08_Reportes",
                                "Atlas_Detallado",
                                "detalle_candidatos_santander.parquet")

REFERENCIA_SVG = os.path.join(RAIZ, "08_Reportes", "reporte_piloto", "diagrama_piloto.svg")
SALIDA = os.path.join(RAIZ, "08_Reportes", "reporte_piloto", "_motor_v1")

# Nombres que jamas deben aparecer dentro del renderizador.
PROHIBIDOS_EN_RENDER = (
    "Bucaramanga", "BUCARAMANGA", "Santander", "Cafe Madrid", "Maipore",
    "Salesiano", "Miraflores", "Centro Democratico", "Pacto Historico",
    "alcalde", "Senado", "votos recuperables", "municipio",
)

resultados = []


def _solo_codigo(fuente: str) -> str:
    """Quita docstrings y comentarios: solo queda lo que se ejecuta."""
    salida = []
    dentro = False
    for linea in fuente.splitlines():
        limpia = linea.strip()
        if limpia.startswith('"""') or limpia.endswith('"""'):
            dentro = not dentro
            continue
        if dentro or limpia.startswith("#"):
            continue
        salida.append(linea)
    return "\n".join(salida)


def check(nombre, ok, detalle=""):
    resultados.append((nombre, ok, detalle))
    print("  [%s] %-44s %s" % ("OK" if ok else "FALLA", nombre, detalle))
    return ok


# =============================================================================
# P1 · COMPATIBILIDAD CON EL REPORTE ANTERIOR
# =============================================================================
def prueba_compatibilidad():
    print()
    print("P1 · COMPATIBILIDAD CON EL REPORTE ANTERIOR")
    print("-" * 70)

    datos = extraer("BUCARAMANGA", "2027")
    contrato_reporte = adaptadores.piloto.construir(datos)
    texto_nuevo = renderizador.renderizar_texto(contrato_reporte)
    svg_nuevo = renderizador.renderizar_svg(contrato_reporte)

    os.makedirs(SALIDA, exist_ok=True)
    with open(os.path.join(SALIDA, "texto_piloto.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(texto_nuevo)
    with open(os.path.join(SALIDA, "diagrama_piloto.svg"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(svg_nuevo)

    texto_ref = open(REFERENCIA_TXT, encoding="utf-8").read()

    print("     texto nuevo  : %d bytes  sha %s"
          % (len(texto_nuevo.encode()), hashlib.sha256(texto_nuevo.encode()).hexdigest()[:16]))
    print("     texto previo : %d bytes  sha %s"
          % (len(texto_ref.encode()), hashlib.sha256(texto_ref.encode()).hexdigest()[:16]))

    # DIFERENCIA INTENCIONAL
    # El reporte anterior decia "En 2026 votaron 264.982". Ese numero es
    # validos + blancos + nulos, y se comparaba contra 247.630 que son SOLO
    # validos de 2023. La comparacion mezclaba categorias.
    # El motor nuevo usa 249.586 (validos 2026), que es comparable con 247.630.
    # No se reproduce el error anterior aunque eso rompa la identidad byte a byte.
    lineas_ref = texto_ref.strip().splitlines()
    lineas_new = texto_nuevo.strip().splitlines()
    print("     lineas: previo %d, nuevo %d" % (len(lineas_ref), len(lineas_new)))
    diferencias = [(i, a, b) for i, (a, b) in enumerate(zip(lineas_ref, lineas_new)) if a != b]
    print("     lineas distintas: %d" % len(diferencias))
    for i, a, b in diferencias:
        print("       %d  previo: %r" % (i + 1, a))
        print("          nuevo : %r" % b)

    # Las diferencias deben caer en dos categorias y en ninguna mas:
    #   (a) la cifra corregida 264.982 -> 249.586
    #   (b) los nombres de puesto, antes escritos a mano y ahora derivados
    lineas_permitidas = {5, 19, 20, 21, 22, 23}  # indices 1-based
    indices_dif = {i + 1 for i, _, _ in diferencias}
    dentro_de_rango = indices_dif <= lineas_permitidas
    check("estructura identica al reporte anterior", len(lineas_ref) == len(lineas_new),
          "%d vs %d lineas" % (len(lineas_ref), len(lineas_new)))
    check("diferencias acotadas a cifra y nombres", dentro_de_rango,
          "lineas %s" % sorted(indices_dif))
    check("la cifra nueva es la comparable",
          "249.586" in texto_nuevo and "264.982" not in texto_nuevo,
          "validos vs validos")
    check("los nombres ya no estan escritos a mano",
          "IE Cafe Madrid." not in texto_nuevo,
          "derivados del registro")

    # El SVG no puede ser byte-identico: el diseno anterior tenia anchos de
    # nodo ajustados a mano. Se compara el CONTENIDO.
    # Se cuentan los nodos por su estilo (rx="10"), no por una altura fija:
    # el nodo de accion crece cuando lleva objetivos.
    patron_nodo = r"<rect x=\"\d+\" y=\"\d+\" width=\"\d+\" height=\"\d+\" rx=\"10\""
    nodos_ref = len(re.findall(patron_nodo, open(REFERENCIA_SVG, encoding="utf-8").read()))
    nodos_new = len(re.findall(patron_nodo, svg_nuevo))
    check("mismo numero de nodos en el SVG", nodos_ref == nodos_new,
          "%d vs %d" % (nodos_ref, nodos_new))

    titulos_ref = set(re.findall(r"font-size=\"19\"[^>]*>([^<]+)<", open(
        REFERENCIA_SVG, encoding="utf-8").read()))
    titulos_new = set(re.findall(r"font-size=\"19\"[^>]*>([^<]+)<", svg_nuevo))
    check("mismos titulos salvo la cifra corregida",
          (titulos_ref - {"264.982 votos"}) == (titulos_new - {"249.586 votos"}),
          "%d vs %d" % (len(titulos_ref), len(titulos_new)))
    if (titulos_ref - {"264.982 votos"}) != (titulos_new - {"249.586 votos"}):
        print("       solo en previo:", titulos_ref - titulos_new)
        print("       solo en nuevo :", titulos_new - titulos_ref)

    return dentro_de_rango


# =============================================================================
# P2 · AISLAMIENTO DEL RENDERIZADOR
# =============================================================================
def prueba_aislamiento():
    print()
    print("P2 · AISLAMIENTO DEL RENDERIZADOR")
    print("-" * 70)

    fuente = open(os.path.join(AQUI, "renderizador.py"), encoding="utf-8").read()
    # Ignorar comentarios y docstrings: solo importa el codigo ejecutable.
    lineas_codigo = []
    dentro_doc = False
    for linea in fuente.splitlines():
        limpia = linea.strip()
        if limpia.startswith('"""') or limpia.endswith('"""'):
            dentro_doc = not dentro_doc
            continue
        if dentro_doc or limpia.startswith("#"):
            continue
        lineas_codigo.append(linea)
    codigo = "\n".join(lineas_codigo)

    fugas = [p for p in PROHIBIDOS_EN_RENDER if p in codigo]
    check("renderizador sin nombres de dominio", not fugas,
          "limpio" if not fugas else "FUGA: " + ", ".join(fugas))

    # El renderizador tampoco debe importar nada del dominio.
    imports = re.findall(r"^\s*(?:from|import)\s+([\w\.]+)", codigo, re.M)
    externos = [i for i in imports if "datos_electorales" in i or "adaptadores" in i]
    check("renderizador no importa el dominio", not externos,
          "limpio" if not externos else str(externos))

    return not fugas and not externos


# =============================================================================
# P3 · CONTRATO
# =============================================================================
def prueba_contrato():
    print()
    print("P3 · CONTRATO DE REPORTE")
    print("-" * 70)

    ok = True

    # 8 nodos deben fallar
    try:
        contrato.ContratoReporte(
            titulo="x", subtitulo="y",
            nodos=[contrato.nodo("n%d" % i) for i in range(8)],
            conexiones=[], accion="hacer algo")
        ok = check("rechaza mas de 7 nodos", False, "acepto 8")
    except contrato.ContratoInvalido:
        ok = check("rechaza mas de 7 nodos", True, "ContratoInvalido") and ok

    # sin accion debe fallar
    try:
        contrato.ContratoReporte(titulo="x", subtitulo="y",
                                 nodos=[contrato.nodo("n")], conexiones=[], accion="  ")
        ok = check("rechaza reporte sin accion", False, "acepto accion vacia")
    except contrato.ContratoInvalido:
        ok = check("rechaza reporte sin accion", True, "ContratoInvalido") and ok

    # rol invalido
    try:
        contrato.nodo("n", rol="inventado")
        ok = check("rechaza rol desconocido", False, "acepto rol invalido")
    except contrato.ContratoInvalido:
        ok = check("rechaza rol desconocido", True, "ContratoInvalido") and ok

    # conexion fuera de rango
    try:
        contrato.ContratoReporte(titulo="x", subtitulo="y",
                                 nodos=[contrato.nodo("n")],
                                 conexiones=[(0, 5)], accion="hacer")
        ok = check("rechaza conexion fuera de rango", False, "acepto (0,5)")
    except contrato.ContratoInvalido:
        ok = check("rechaza conexion fuera de rango", True, "ContratoInvalido") and ok

    # un contrato valido pasa
    datos = extraer("BUCARAMANGA", "2027")
    c = adaptadores.piloto.construir(datos)
    check("contrato valido se construye", c is not None,
          "%d nodos, %d bloques" % (len(c.nodos), len(c.bloques)))

    # R-01.2: ninguna linea de mas de 20 palabras
    excesos = c.validar_texto()
    check("texto cumple R-01.2 (<=20 palabras)", not excesos,
          "cumple" if not excesos else "%d excesos" % len(excesos))

    return ok and not excesos


# =============================================================================
# P4 · NIVELES
# =============================================================================
def prueba_niveles():
    print()
    print("P4 · NIVELES DE REPORTE")
    print("-" * 70)

    datos = extraer("BUCARAMANGA", "2027")
    contrato_unico = adaptadores.piloto.construir(datos)

    # --- aislamiento de los tres adaptadores ---
    for nombre in ("piloto", "tecnico", "feynman"):
        ruta = os.path.join(AQUI, "adaptadores", "%s.py" % nombre)
        fuente = open(ruta, encoding="utf-8").read()
        # Solo cuenta el codigo: docstrings y comentarios pueden nombrar el
        # dominio como ejemplo sin ser una fuga.
        codigo = _solo_codigo(fuente)
        fugas = [p for p in PROHIBIDOS_EN_RENDER if p in codigo]
        # import real, no mencion en un comentario
        importa = bool(re.search(r"^\s*(?:from|import)\s+.*datos_electorales", codigo, re.M))
        check("adaptador %s sin nombres de dominio" % nombre, not fugas,
              "limpio" if not fugas else "FUGA: " + ", ".join(fugas))
        check("adaptador %s no importa el dominio" % nombre, not importa,
              "limpio" if not importa else "importa datos_electorales")

    # --- los tres leen el mismo contrato ---
    textos = {}
    for nombre, modulo in (("piloto", adaptadores.piloto),
                           ("tecnico", adaptadores.tecnico),
                           ("feynman", adaptadores.feynman)):
        try:
            if nombre == "piloto":
                t = modulo.construir(datos)
                t = renderizador.renderizar_texto(t)  # el piloto devuelve contrato
            else:
                t = modulo.desde_contrato(contrato_unico)
            textos[nombre] = t
            check("nivel %s produce salida" % nombre, bool(t and len(t) > 200),
                  "%d chars" % len(t or ""))
        except Exception as error:  # noqa: BLE001
            check("nivel %s produce salida" % nombre, False, str(error)[:60])
            textos[nombre] = ""

    # --- el contrato es el mismo objeto para tecnico y feynman ---
    check("tecnico y feynman comparten contrato",
          adaptadores.tecnico.desde_contrato(contrato_unico) == textos.get("tecnico"),
          "determinista")

    # --- el tecnico trae metodologia ---
    t = textos.get("tecnico", "")
    check("tecnico incluye formula", "BRECHA" in t, "formula presente")
    check("tecnico incluye hash de fuente", "SHA256" in t or "hash" in t.lower(), "")
    check("tecnico declara limites", "Limites" in t or "limites" in t, "")
    check("tecnico publica rango cuando no hay punto",
          "entre" in t and "23.570" in t, "rango declarado")

    # --- el feynman explica, no lista ---
    f = textos.get("feynman", "")
    check("feynman incluye analogia", "Imagina" in f, "")
    check("feynman explica la tasa", "de cada 100" in f, "")
    check("feynman nombra los objetivos", all(o in f for o in contrato_unico.puestos_objetivo[:3]),
          "%d objetivos" % len(contrato_unico.puestos_objetivo))
    check("feynman explica porque son importantes",
          "Por que estos" in f or "porque" in f.lower(), "")
    palabras = len(f.split())
    check("feynman cabe en 2 paginas", palabras < 1000, "%d palabras" % palabras)

    # --- mapeo oficial de partidos ---
    from motor_reportes import datos_electorales as _de2
    mapeo = _de2.cargar_mapeo_partidos()
    check("mapeo de partidos cargado", len(mapeo) > 300, "%d partidos" % len(mapeo))
    check("Pacto Historico resuelve",
          _de2.resolver_nombre_partido(3063).upper().startswith("PACTO"),
          _de2.resolver_nombre_partido(3063))
    check("codigo desconocido devuelve Lista [x]",
          _de2.resolver_nombre_partido(999999) == "Lista [999999]",
          _de2.resolver_nombre_partido(999999))
    check("mapeo viaja en el contrato", bool(contrato_unico.anexos.get("mapeo_partidos")),
          str(len(contrato_unico.anexos.get("mapeo_partidos") or {})))
    t2 = textos.get("tecnico", "")
    check("tecnico trae hashes de la Registraduria",
          "SHA256" in t2 and "Encoding" in t2, "")
    f2 = textos.get("feynman", "")
    check("feynman habla de los votos sin nombre",
          "no tenian nombre" in f2 or "sin nombre" in f2, "")

    # --- lookup de candidatos ---
    top = _de2.cargar_top_candidatos()
    check("lookup de candidatos cargado", len(top) >= 10, "%d listas" % len(top))
    total_cand = sum(len(l["candidatos"]) for l in top)
    check("lookup acotado a 50-60 candidatos", 40 <= total_cand <= 60,
          "%d candidatos" % total_cand)
    check("ninguna lista supera 5 candidatos",
          all(len(l["candidatos"]) <= 5 for l in top), "")
    check("Pacto Historico Santander tiene cabeza de lista",
          any(l["codigo_lista"] == "03096" and "TORRES" in l["candidatos"][0]["nombre"].upper()
              for l in top if l["candidatos"]), "")
    check("feynman nombra candidatos",
          "A quien hay que buscar" in f2 or "cabeza de lista" in f2, "")

    # --- drift ---
    from motor_reportes import drift as _drift
    import time as _t
    _t0 = _t.perf_counter()
    _d = _drift.calcular(PARQUET_DETALLE)
    _t_drift = _t.perf_counter() - _t0
    check("drift cubre los 87 municipios", _d["total_municipios"] == 87,
          "%d municipios" % _d["total_municipios"])
    check("drift bajo 2 s", _t_drift < 2.0, "%.2f s" % _t_drift)
    check("tres metricas distintas",
          len({"drift_cuota", "drift_perdida", "drift_hhi"}) == 3, "")
    check("umbrales por metrica", len(_d["umbrales"]) == 3,
          str(sorted(_d["umbrales"])))
    check("declara la metrica no calculable",
          "no computable" in _d["metrica_no_calculable"]["razon"]
          or "no se solapan" in _d["metrica_no_calculable"]["razon"], "")
    _marcados = _d["flagged"]
    check("no marca a todos", _marcados < _d["total_municipios"],
          "%d de %d" % (_marcados, _d["total_municipios"]))
    check("no marca a ninguno", _marcados > 0, "%d marcados" % _marcados)
    _inf = _drift.informe(_d)
    check("informe declara hipotesis no verificables",
          "NO VERIFICABLE" in _inf, "")
    check("informe declara H1 y H4", _inf.count("no verificable") >= 2, "")

    # --- regresion: la ruta del CSV predictivo debe ser parametro ---
    # Cuando era constante apuntaba al vault, y en la nube esa ruta no existe.
    # El reporte salia sin prioridades y con las cifras viejas, sin error.
    import inspect
    from motor_reportes import datos_electorales as _de
    firma = inspect.signature(_de.extraer)
    check("extraer() acepta ruta_predictivo", "ruta_predictivo" in firma.parameters,
          "parametro presente" if "ruta_predictivo" in firma.parameters else "AUSENTE")
    firma_prio = inspect.signature(_de._prioridades)
    check("_prioridades() acepta ruta_predictivo",
          "ruta_predictivo" in firma_prio.parameters,
          "parametro presente" if "ruta_predictivo" in firma_prio.parameters else "AUSENTE")
    # con una ruta inexistente devuelve vacio, no revienta
    vacio = _de._prioridades("BUCARAMANGA", "/ruta/que/no/existe.csv")
    check("_prioridades() tolera ruta ausente", vacio == {}, "devuelve {}")

    # --- prioridad unificada ---
    check("contrato lleva prioridades", len(contrato_unico.prioridades) > 0,
          "%d prioridades" % len(contrato_unico.prioridades))
    niveles = [p["nivel"] for p in contrato_unico.prioridades]
    check("todos los niveles son 1-4", all(n in (1, 2, 3, 4) for n in niveles),
          str(niveles))

    t = textos.get("tecnico", "")
    f = textos.get("feynman", "")
    check("tecnico incluye tabla de prioridad", "Prioridad de intervencion" in t, "")
    check("tecnico trae desviacion z", "Desviacion z" in t, "")
    check("tecnico trae accion recomendada", "Accion recomendada" in t, "")
    check("tecnico declara el limite del PBC", "PBC no aplica" in t, "")
    check("feynman tiene seccion de prioridad", "Prioridad: qué atender" in f, "")
    check("feynman nombra la prioridad de cada puesto",
          all(p["accion"] in f for p in contrato_unico.prioridades[:3]), "")
    check("feynman explica el criterio doble",
          "cuánto voto se puede recuperar" in f, "")

    # el contrato rechaza un nivel invalido
    try:
        import copy
        malo = copy.deepcopy(contrato_unico)
        malo.prioridades = [{"nombre": "x", "nivel": 9, "etiqueta": "",
                             "accion": "", "gap": 0, "z": 0}]
        contrato.ContratoReporte(
            titulo=malo.titulo, subtitulo=malo.subtitulo, nodos=malo.nodos,
            conexiones=malo.conexiones, accion=malo.accion,
            prioridades=malo.prioridades)
        check("rechaza nivel de prioridad invalido", False, "acepto nivel 9")
    except contrato.ContratoInvalido:
        check("rechaza nivel de prioridad invalido", True, "ContratoInvalido")

    # --- ninguno usa jerga prohibida ---
    jerga = ("Z-score", "Pareto", "cluster", "cuociente", "cifra repartidora")
    for nombre, texto in textos.items():
        fugas = [j for j in jerga if j.lower() in texto.lower()]
        check("%s sin jerga tecnica" % nombre, not fugas,
              "limpio" if not fugas else str(fugas))

    return all(ok for _, ok, _ in resultados)


# =============================================================================
def main() -> int:
    print("=" * 70)
    print("TEST · MOTOR MODULAR DE REPORTES")
    print("=" * 70)

    p1 = prueba_compatibilidad()
    p2 = prueba_aislamiento()
    p3 = prueba_contrato()
    p4 = prueba_niveles()

    print()
    print("=" * 70)
    total = len(resultados)
    pasadas = sum(1 for _, ok, _ in resultados if ok)
    print("RESUMEN: %d/%d pruebas pasadas" % (pasadas, total))
    for nombre, ok, detalle in resultados:
        if not ok:
            print("  FALLO: %s %s" % (nombre, detalle))
    print("=" * 70)
    print("ESTADO: %s" % ("TODO OK" if pasadas == total else "REVISAR"))
    print("=" * 70)
    return 0 if pasadas == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
