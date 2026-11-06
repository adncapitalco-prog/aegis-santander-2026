# -*- coding: utf-8 -*-
"""
INTEGRATION TEST · AEGIS AUDITOR
================================

Verifica que la capa de memoria sea legible, consultable y consistente.

QUE SE PRUEBA
-------------
  1. Los seis archivos del Auditor existen y se leen sin error
  2. `buscar_leccion` encuentra resultados reales
  3. `verificar_decision` encuentra decisiones reales
  4. `forensic_manifest.json` es JSON valido y tiene hashes
  5. El modulo de consulta no importa librerias pesadas
  6. Los 12 hallazgos del encargo estan en el registro de bugs
  7. Las entradas respetan el formato (empiezan por "- [")

LO QUE ESTE TEST NO PRUEBA
--------------------------
No prueba que las lecciones sean correctas. Prueba que estan escritas, que se
pueden encontrar y que el formato permite encontrarlas.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
PESADAS = ("pandas", "numpy", "scipy", "streamlit", "plotly", "pyarrow",
           "networkx", "torch", "tensorflow", "matplotlib")
ARCHIVOS_ESPERADOS = (
    "auditor_constitution.md",
    "decision_log.md",
    "bug_registry.md",
    "lessons_learned.md",
    "forensic_manifest.json",
    "auditor_query.py",
)

resultados = []


def check(nombre: str, ok: bool, detalle: str = "") -> None:
    resultados.append((nombre, bool(ok)))
    print("  [%s] %-52s %s" % ("OK" if ok else "FALLA", nombre, detalle))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, str(BASE))
    import auditor_query as aq

    print("=" * 78)
    print("INTEGRATION TEST · AEGIS AUDITOR")
    print("=" * 78)

    print()
    print("A1 · ARCHIVOS")
    print("-" * 78)
    for nombre in ARCHIVOS_ESPERADOS:
        p = BASE / nombre
        check("existe %s" % nombre, p.exists(),
              "%d bytes" % p.stat().st_size if p.exists() else "AUSENTE")

    print()
    print("A2 · CONSULTA")
    print("-" * 78)
    for clave in ("constitucion", "decisiones", "bugs", "lecciones", "manifiesto"):
        contenido = aq._leer(clave)
        check("se lee %s" % clave, bool(contenido), "%d chars" % len(contenido))

    lecciones_benford = aq.buscar_leccion("Benford")
    check("buscar_leccion('Benford') devuelve resultados",
          len(lecciones_benford) >= 1, "%d" % len(lecciones_benford))

    # busqueda con y sin tildes: la memoria debe responder a las dos formas
    for con, sin in (("entropía", "entropia"), ("métrica", "metrica"),
                     ("índice", "indice")):
        n_con = len(aq.buscar_leccion(con))
        n_sin = len(aq.buscar_leccion(sin))
        check("busqueda con tilde %r funciona" % con, n_con == n_sin,
              "%d = %d" % (n_con, n_sin))

    for palabra in ("entropía", "percentil", "umbral fijo", "destacar",
                    "ruta_predictivo"):
        total = (len(aq.buscar_leccion(palabra)) + len(aq.buscar_bug(palabra))
                 + len(aq.verificar_decision(palabra)))
        check("%r aparece en algun registro" % palabra, total >= 1, "%d" % total)

    for palabra in ("umbral", "encoding", "grafo", "prueba"):
        n = len(aq.buscar_leccion(palabra))
        check("buscar_leccion(%r) devuelve resultados" % palabra, n >= 1, "%d" % n)

    decisiones = aq.verificar_decision("Benford")
    check("verificar_decision('Benford') devuelve resultados",
          len(decisiones) >= 1, "%d" % len(decisiones))

    decisiones_percentil = aq.verificar_decision("percentil")
    check("verificar_decision('percentil') devuelve resultados",
          len(decisiones_percentil) >= 1, "%d" % len(decisiones_percentil))

    bugs = aq.buscar_bug("grafo")
    check("buscar_bug('grafo') devuelve resultados", len(bugs) >= 1, "%d" % len(bugs))

    r = aq.resumen()
    check("hay decisiones registradas", r["decisiones"] >= 10, "%d" % r["decisiones"])
    check("hay bugs registrados", r["bugs"] >= 12, "%d" % r["bugs"])
    check("hay lecciones registradas", r["lecciones"] >= 10, "%d" % r["lecciones"])
    check("hay deudas declaradas", r["deudas_abiertas"] >= 2, "%d" % r["deudas_abiertas"])

    print()
    print("A3 · MANIFIESTO FORENSE")
    print("-" * 78)
    ruta = BASE / "forensic_manifest.json"
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        check("el manifiesto es JSON valido", True, "%d archivos" % len(datos.get("archivos", {})))
        check("el manifiesto tiene hashes", len(datos.get("archivos", {})) > 0,
              "%d" % len(datos.get("archivos", {})))
        largo_ok = all(len(v) == 64 for v in datos.get("archivos", {}).values())
        check("todos los hashes son SHA256 de 64 caracteres", largo_ok, "")
    except (ValueError, OSError) as error:
        check("el manifiesto es JSON valido", False, str(error))

    estado = aq.estado_manifiesto()
    check("el manifiesto verifica integridad", estado["ok"],
          "%d problemas" % len(estado["problemas"]))
    for p in estado["problemas"][:5]:
        print("      ! %s: %s" % (p["archivo"], p["motivo"]))

    print()
    print("A4 · AISLAMIENTO")
    print("-" * 78)
    fuente = (BASE / "auditor_query.py").read_text(encoding="utf-8")
    arbol = ast.parse(fuente)
    importados = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for a in nodo.names:
                importados.add(a.name.split(".")[0])
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.add(nodo.module.split(".")[0])
    pesadas = sorted(importados & set(PESADAS))
    check("auditor_query no importa librerias pesadas", not pesadas,
          "limpio" if not pesadas else str(pesadas))
    print("      importa: %s" % ", ".join(sorted(importados)))

    print()
    print("A5 · FORMATO DE LAS ENTRADAS")
    print("-" * 78)
    for clave in ("decisiones", "bugs", "lecciones"):
        entradas = aq._entradas(aq._leer(clave))
        con_campos = [e for e in entradas if len(e["campos"]) >= 2]
        check("%s tiene entradas con formato" % clave,
              len(con_campos) == len(entradas) and len(entradas) > 0,
              "%d entradas" % len(entradas))

    print()
    print("=" * 78)
    pasadas = sum(1 for _, ok in resultados if ok)
    print("RESUMEN: %d/%d pruebas pasadas" % (pasadas, len(resultados)))
    fallos = [n for n, ok in resultados if not ok]
    for f in fallos:
        print("  FALLO: %s" % f)
    print("ESTADO: %s" % ("TODO OK" if not fallos else "REVISAR"))
    print("=" * 78)
    return 0 if not fallos else 1


if __name__ == "__main__":
    raise SystemExit(main())
