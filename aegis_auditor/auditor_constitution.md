# AEGIS AUDITOR · MARCO NORMATIVO

**Versión 1.0 · 2026-11-06**

---

## QUÉ ES

Una capa de memoria institucional. El DSH no recuerda entre sesiones y el
AEGIS-CORE SDD no debe modificarse por aprendizajes tácticos. El Auditor
existe para que lo aprendido no se pierda con la sesión y no contamine el
núcleo.

Cuatro registros:

| Archivo | Qué guarda |
|---|---|
| `decision_log.md` | Decisiones arquitectónicas con su razón y sus alternativas descartadas |
| `bug_registry.md` | Defectos encontrados, su causa raíz y su prueba de regresión |
| `lessons_learned.md` | Reglas generales que evitan repetir el error |
| `forensic_manifest.json` | Hash SHA256 de todo lo que el sistema ha producido |

---

## QUÉ NO ES

**No es el CORE.** El CORE define qué es AEGIS. El Auditor registra qué le
pasó a AEGIS mientras se construía. Un cambio en el CORE es una decisión
constitucional; un cambio en el Auditor es una nota de bitácora.

**No es configuración.** Ningún módulo lee el Auditor para decidir cómo
funcionar. Si el Auditor desaparece, el sistema sigue produciendo los mismos
números. Es memoria, no lógica.

**No es un dashboard.** No se ejecuta en Streamlit, no se sirve por HTTP, no
tiene interfaz. Es una herramienta de desarrollo.

**No es un juez.** Registra lo que se decidió y por qué. No declara
automáticamente que una decisión pasada sea todavía correcta.

---

## RELACIÓN CON EL CORE

```
AEGIS-CORE SDD        inmutable · constitucional · no lo toca el Auditor
        │
        ▼
AEGIS AUDITOR         append-only · memoria · solo lectura para el DSH
        │
        ▼
motor_reportes/       operativo · no consulta el Auditor
aegis_intellect/      operativo · no consulta el Auditor
```

**Regla de dirección:** el Auditor nunca modifica el CORE. El CORE nunca
consulta el Auditor. El flujo va en un solo sentido: lo que ocurre en la
operación se anota en el Auditor.

---

## PROTOCOLO DE CONSULTA

**El DSH consulta el Auditor al inicio de cada sesión nueva, antes de tocar
código.** Orden:

1. `lessons_learned.md` — para no repetir un error conocido.
2. `decision_log.md` — para no revertir una decisión sin saber por qué se tomó.
3. `bug_registry.md` — para saber qué pruebas de regresión existen.
4. `forensic_manifest.json` — para detectar si algo cambió desde la última sesión.

**El DSH NO modifica el Auditor durante la consulta.** La escritura ocurre
solo al cerrar una sesión, y solo mediante `auditor_query.py`.

---

## REGLAS DE ESCRITURA

**1 · Append-only.** Una entrada no se borra ni se reescribe. Si una decisión
resultó equivocada, se añade una entrada nueva que la contradice y se marca
la anterior como `SUPERADA`. Borrar el error es perder la lección.

**2 · Formato fijo.** Cada entrada empieza por `- [` para que el módulo de
consulta pueda encontrarla con una expresión regular. Sin formato no hay
consulta, y sin consulta esto es un diario, no una memoria.

**3 · Toda entrada lleva fecha.** Una lección sin fecha no se puede situar
respecto a las demás.

**4 · Todo archivo tiene hash en el manifiesto.** Si un archivo del Auditor
cambia sin actualizar su hash, la verificación retrospectiva falla. Ese fallo
es la señal.

**5 · Lo que no se puede verificar no se escribe como hecho.** Se escribe
como hipótesis, con la palabra `HIPOTESIS` en la entrada.

---

## LO QUE ESTE AUDITOR NO RESUELVE

**No impide repetir un error.** Documenta para que el DSH pueda evitarlo, pero
un DSH que no consulte no obtiene nada. La memoria sirve si se lee.

**No valida el pasado.** Un hash correcto prueba que un archivo no cambió; no
prueba que su contenido fuera correcto cuando se generó.

**No sustituye las pruebas.** Una lección escrita no es una prueba de
regresión. Cada bug resuelto debe tener su `check()` en el código.
