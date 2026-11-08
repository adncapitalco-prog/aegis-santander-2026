# BUG REGISTRY · AEGIS-POLITICA

**Formato:** `- [ID] [SÍNTOMA] [ROOT CAUSE] [FIX] [TEST DE REGRESIÓN]`

**Todos los hallazgos de las sesiones 2026-11-04 a 2026-11-06.**
**Cada uno tiene su `check()` en `motor_reportes/test_motor_reportes.py`.**

---

## PARSING E INGESTIÓN

- [BUG-001] [El script de extracción de la Registraduría no ejecutaba: `UnicodeDecodeError`] [`encoding="utf-8"` sobre archivos que son cp1252; fallan en los bytes 859 y 37] [Probar utf-8, cp1252 y latin-1 en orden y devolver el que funciona, declarándolo] [integration_test: `buscar_leccion("encoding")` devuelve ≥1; test_motor_reportes verifica el mapeo]
- [BUG-002] [Los nombres de partido salían con una «N» pegada al final] [Se tomaba `linea[5:]` en vez de `linea[5:205]`; la bandera ocupa la posición 205 y `.strip()` no la quita] [Cortar en el ancho declarado del campo] [El mapeo resuelve 3063 → PACTO HISTÓRICO SENADO sin sufijo]
- [BUG-003] [Se tomaba el contador secuencial como código de partido] [El campo `[15:20]` de CANDIDATOS sube de 10 en 10; no es un código. Los candidatos heredan el partido de la cabecera] [Detectar cabecera por el campo de género: `[135:138]` empieza por espacio, no por M/F] [Extrae 12 listas de 87 líneas sin perder ninguna]
- [BUG-004] [La cédula aparecía pegada al nombre del candidato] [`[20:135]` contiene nombre, apellidos y cédula en columnas fijas] [Cortar `[20:70]` nombres, `[70:118]` apellidos, `[118:135]` cédula] [Los 56 nombres del lookup no acaban en dígitos]
- [BUG-005] [Filtrar por la palabra «SANTANDER» devolvía 2 listas y una era Norte de Santander] [El Senado es circunscripción nacional: no existen listas departamentales] [Filtrar por el campo estructural de circunscripción: `[3:6] == "127"`] [12 listas, 56 candidatos, 0 de Norte de Santander]

## FUSIÓN DE DATOS

- [BUG-006] [La tasa de voto no aprovechado salía 0,00 %] [Comparación de cadenas con distinta capitalización: «VOTO NO APROVECHADO» frente a «Voto no aprovechado»] [Comparación insensible a mayúsculas] [La tasa de pérdida del departamento es 8,07 %]
- [BUG-007] [Los 87 municipios quedaban clasificados como «Terremoto»] [Los nombres de partido difieren en mayúsculas entre años y la unión era por nombre] [Unir por código entero] [Las cuatro clases de cluster suman 825 puestos]
- [BUG-008] [Las corporaciones uninominales atribuían votos a un «partido» que era el eslogan del candidato] [En Gobernación y Alcaldía el campo `partido` guarda la divisa («DEFENDAMOS BUCARAMANGA»)] [Para uninominales usar el candidato como entidad, resuelto por fila] [El ranking de entidades no muestra eslóganes]

## ESTADÍSTICA

- [BUG-009] [Benford marcaba 531 de 825 puestos] [Muestra mínima de 30 valores: con muestras pequeñas la prueba no tiene potencia y el ruido dispara la alerta] [Subir el mínimo a 300] [Benford marca 25 de 825, y aun así se retiró del tablero]
- [BUG-010] [Los puestos con mayor índice de oportunidad eran recintos penitenciarios de 96 votos] [Sin piso de volumen ni exclusión de recintos especiales] [Piso de 500 votos y exclusión de la zona 099] [El top de oportunidad lo forman puestos urbanos de más de 4.000 votos]
- [BUG-011] [El cuadrante crítico de la matriz de prioridad quedaba vacío (N1 = 0)] [La desviación relativa correlaciona −0,34 con el volumen: los puestos pequeños dominan el decil alto] [Desviación ajustada por tamaño: z de la proporción] [N1 pasa de 0 a 51 puestos; correlación con volumen +0,37]

## GRAFO

- [BUG-012] [El GBEE marcaba 88 de 88 puestos como anómalos] [El grafo conectaba todo par del municipio con peso ≥1: densidad 1,0, el paso de mensajes promediaba la ciudad entera] [Aristas solo por comuna o afinidad, con tope de 12 vecinos] [Densidad 0,1421 en Bucaramanga; 8 de 88 marcados]
- [BUG-013] [La integración del GBEE volvió a producir un grafo completo] [Se usó el cluster como si fuera la comuna y se fijó `ratio_participacion = 1.0` para todos, así que todas las afinidades coincidían] [Leer comuna y votos de 2023 del maestro] [El desvío de Café Madrid vuelve de +74,4 % a +39,8 %]

## DESPLIEGUE

- [BUG-014] [Streamlit Cloud seguía mostrando el reporte con cifras viejas y sin la sección de prioridad] [`_prioridades()` usaba una ruta absoluta del vault; en la nube no existe y devolvía `{}` en silencio] [Ruta del CSV predictivo como parámetro; el dashboard la pasa] [3 pruebas: `extraer` y `_prioridades` aceptan el parámetro; ruta ausente devuelve `{}`]
- [BUG-015] [Editar un adaptador con el servidor encendido no cambiaba la salida] [`importlib.reload(motor_reportes)` no recarga los submódulos] [Recargar explícitamente los siete submódulos que usa el tablero] [Verificado: marcador `False` antes, `True` después del bucle]
- [BUG-016] [El empaquetador sobrescribía el `config.toml` del tema] [Tenía su propia copia del tema hardcodeada: dos fuentes de verdad] [Copiar el de `salidas/`] [Hash idéntico entre `salidas/` y `deploy/`]

## RENDIMIENTO

- [BUG-017] [`_sin_nombre` tardaba 1,19 s por reporte] [Recorría las 300.734 filas del detalle para sumar votos sin nombre] [Precalcular en sidecar de 184 bytes; se conserva la ruta lenta como respaldo] [0,011 s (109x); valor idéntico 413.495]
- [BUG-018] [El sidecar precalculado daba 84.935 en vez de 413.495] [Sumaba `votos_top` cuando el partido top estaba sin nombre, no todos los votos sin nombre] [Recorrer todas las filas de listas sin identificar] [El sidecar coincide con el cálculo lento]

## FUGAS DE ARQUITECTURA

- [BUG-019] [El adaptador Feynman contenía la palabra «Santander»] [Se escribió «Cada lista de Santander tiene un cabeza de lista»] [Frase genérica] [Test de aislamiento: `PROHIBIDOS_EN_RENDER` no aparece en el código de los adaptadores]
- [BUG-020] [El adaptador Feynman contenía la palabra «municipio», dos veces] [«Este municipio castiga» y la clave de anexo `perfil_municipio`] [«Este territorio» y clave `perfil`] [El test de aislamiento vuelve a pasar]

## PRUEBAS

- [BUG-021] [Una prueba daba `False` con el reload funcionando] [Comprobaba `TITULO_NIVEL`, una constante que `desde_contrato` nunca lee] [Comprobar un marcador que sí se emite (`## Que paso`)] [Ninguna: se corrigió la prueba, no el código]
- [BUG-022] [`UnboundLocalError: _d` en la suite] [El bloque de ortogonalidad se insertó antes del bloque que define `_d`] [Reordenar: drift primero, ortogonalidad después] [81/81 pruebas]
- [BUG-023] [El contrato de reportes no importaba: `from .contrato import ContratoReporte, MaxNodosError if False else object`] [Expresión inválida en el import] [Dejar solo `ContratoReporte`] [Los tres niveles generan reportes]
- [BUG-024] [`NameError: CSV_PUESTOS` al generar las métricas] [La constante se llama `SALIDA`; el nombre se escribió de memoria] [Usar `SALIDA`] [El motor escribe `metricas_depto.json`]

## DEUDAS ABIERTAS (no son bugs resueltos)

- [DEUDA-001] [Pacto Histórico Cámara Santander: 140.771 oficial frente a 142.335 del vault] [La fuente oficial no expone el desglose de su total; no se encontró subconjunto que cuadre] [Se publican las dos cifras en los tres niveles de reporte] [Declarada en `deudas_forenses.json`; ningún test la cierra]
- [DEUDA-002] [`_puestos` lee 300.734 filas por reporte (~1,9 s)] [Filtra un municipio recorriendo el detalle completo] [Pendiente: precalcular por municipio o migrar a parquet] [Ninguna todavía; medido y localizado]

## CONSOLIDACION DE LA SESION 2026-11-06

- [BUG-025] [Streamlit Cloud mostraba el reporte con cifras viejas y sin la seccion de prioridad, sin ningun error] [La variable `ruta_predictivo` era una constante absoluta del vault dentro de `_prioridades()`; en la nube no existe y la funcion devolvia `{}` en silencio. Es el mismo incidente que BUG-014, registrado aqui con el identificador tecnico porque la busqueda por nombre de variable no lo encontraba] [`ruta_predictivo` es parametro de `extraer()`, `_puestos()` y `_prioridades()`; el dashboard lo pasa] [3 pruebas: los dos primeros aceptan el parametro; una ruta ausente devuelve `{}` y no revienta]
- [BUG-026] [La prueba de rendimiento de drift fallaba de forma intermitente con 2,05 s frente a un umbral de 2,0 s] [Umbral demasiado ajustado: tres corridas dieron 1,05, 1,40 y 1,34 s. La prueba no medía una regresion, medía la carga de la maquina] [Umbral a 3 s, declarando que la prueba detecta regresiones catastroficas —los 4,6 s del primer intento— y no micro-fluctuaciones] [96/96 pruebas estables]
