# LESSONS LEARNED · AEGIS-POLITICA

**Formato:** `- [LECCIÓN] [CONTEXTO] [REGLA PARA FUTURO]`

**Ordenadas por cuántas veces se repitieron, no por fecha.**

---

## UN UMBRAL FIJO ES UNA OPINIÓN DISFRAZADA DE MEDIDA

- [Un umbral elegido a priori no distingue nada: hay que calibrarlo contra la distribución] [Cinco veces en este proyecto: Benford al 5 % marcó 25 de 825; el umbral de red al 25 % marcó 34 de 88 (39 %); el grafo completo marcó 88 de 88; la volatilidad de partido líder da 97 % en todos los pares; la volatilidad de clase media con desaparecidas no bajó de 7,38 pp] [Todo umbral sale de un percentil de la distribución observada, y el percentil se declara en el resultado. Si alguien propone un valor fijo, la pregunta es: ¿contra qué distribución lo mediste?]

- [Una métrica que marca al 40 % de la población no informa] [El umbral de red marcaba 34 de 88 puestos; el revisor aprende a ignorar la alerta] [Antes de entregar una alerta, medir cuántos casos dispara. Si es más de ~15 %, el umbral está mal, no los datos.]

## LA PRUEBA TIENE QUE MEDIR LO QUE CREES QUE MIDE

- [Una prueba puede fallar porque comprueba algo que no se usa] [Cuatro intentos de verificar el reload daban `False`; la prueba tocaba `TITULO_NIVEL`, una constante que `desde_contrato` nunca lee] [Antes de depurar código, verificar que el marcador de la prueba aparezca en la salida esperada. Si el marcador no puede aparecer, la prueba no mide nada.]

- [Un valor conocido es el mejor test de una optimización] [El sidecar precalculado daba 84.935 en vez de 413.495 y no fallaba nada; se detectó por comparar contra el número conocido] [Toda optimización se valida contra el valor anterior. Si el número cambia, la optimización está mal, no los datos.]

## COMPARAR LO COMPARABLE

- [No comparar identidades que no existen en ambos lados] [«Partido líder» entre Asamblea 2023 (16 códigos) y Cámara 2026 (68 códigos, 4 comunes) da 97 % de cambio; no mide volatilidad, mide que los universos no se solapan] [Antes de comparar dos conjuntos, contar cuántos elementos tienen en común. Si el solapamiento es bajo, la comparación de identidades no es válida y hay que medir magnitudes.]

- [Dos códigos con nombres casi iguales son dos cosas distintas] [Se reportaron 142.335 y 157.017 del «Pacto Histórico» como contradictorios durante tres turnos; 3096 es Cámara y 3063 es Senado] [Toda cifra de partido lleva corporación además de código. Sin corporación, el código no identifica nada.]

- [Un cero no es «no hay datos», es «hay cero»] [La resiliencia daba 0 donde el líder de 2023 no compitió en 2026] [Si un indicador no se puede calcular, se escribe NO CALCULABLE. Un cero afirma algo que no se midió.]

## EL FALLO SILENCIOSO ES EL PEOR

- [Un `except` que devuelve vacío convierte un error de despliegue en un misterio] [`_prioridades()` devolvía `{}` cuando la ruta no existía; costó tres despliegues descubrir que la nube mostraba cifras viejas sin ningún error] [Cuando una función degrada, debe declararlo. Un valor por defecto silencioso es una deuda que se paga en producción.]

- [La ruta de un dato es un parámetro, nunca una constante] [Una ruta absoluta del vault en el motor hacía que la nube no encontrara el archivo] [Toda ruta de entrada se pasa como argumento, con un valor por defecto que se pueda comprobar.]

## PRECALCULAR ANTES QUE OPTIMIZAR LA LECTURA

- [Si el dato no cambia entre ejecuciones, se calcula una vez] [`_sin_nombre` recorría 300.734 filas por reporte (1,19 s); un sidecar de 184 bytes lo dejó en 0,011 s, 109 veces más rápido] [Antes de optimizar un lector, preguntar si el resultado se puede guardar. Optimizar la lectura es la segunda opción, no la primera.]

## MEDIR ANTES DE AFIRMAR

- [Una medición contaminada invierte la conclusión] [El primer benchmark de parquet dio 0,87x (descartado) porque tres DataFrames de 300.000 filas seguían vivos en el mismo proceso; aislado por proceso dio 4,90x en frío y 12,69x en caliente] [Un benchmark se corre en un proceso limpio y con el mismo trabajo en ambos lados. Si el resultado contradice la intuición, sospechar del banco de pruebas antes que del objeto medido.]

- [El primer grafo era completo y no lo noté hasta medir la densidad] [El paso de mensajes promediaba la ciudad entera y marcaba 88 de 88] [Medir la estructura antes de interpretar sus resultados: densidad, grado medio, grado máximo. Un grafo completo no aporta información.]

## VOCABULARIO

- [Un nombre con prestigio no convierte un dato en ciencia] [Se propuso «ADN cultural» y «vectores meméticos» para lo que son tasas de abstención y cambios de partido] [Nombrar cada indicador por lo que mide. Si el nombre necesita una metáfora para sonar profundo, el indicador no lo es.]

- [El adaptador no conoce el dominio] [Dos veces apareció «municipio» en el adaptador Feynman; una vez «Santander»] [La prueba de aislamiento no es burocracia: es la que impide que la capa de presentación se llene de casos particulares.]

## CONSTRUIR SOBRE DEUDA

- [Una cifra que no cuadra se declara, no se elige] [Pacto Histórico: 140.771 frente a 142.335, diferencia de 1.564 sin explicar tras siete verificaciones] [Una deuda forense abierta es un entregable válido. Elegir la cifra que conviene es peor que publicar las dos.]

- [No escalar mientras queden deudas sin declarar] [El playbook de escalado advierte que un p80 de 87 municipios no significa lo mismo que un p80 de 125] [Antes de un departamento nuevo: cerrar o declarar cada deuda, y recalibrar cada percentil sobre la distribución nueva.]

## EL ENCODING SE VERIFICA ANTES DE PARSEAR

- [El encoding de un archivo ajeno se verifica antes de parsear: uno que "debería ser UTF-8" puede no serlo, y el fallo aparece en el byte 37] [Los TXT de la Registraduría fallan al decodificar como UTF-8; son cp1252] [Antes de parsear un archivo ajeno, probar utf-8, cp1252 y latin-1 en orden, y declarar cuál funcionó. Un archivo mal decodificado produce nombres con símbolos raros que parecen errores de datos y son errores de lectura.]

- [El ancho de campo no se adivina: se mide] [PARTIDOS tiene 206 caracteres fijos; el nombre ocupa `[5:205]` y la bandera la posición 205. Tomar `[5:]` pegaba la bandera al nombre] [Medir la longitud de las líneas y localizar cada campo por posición antes de escribir el parser. Un `.strip()` no arregla un corte mal hecho.]

## NO DESTACAR EL MAXIMO GLOBAL

- [Un indice calculado sobre toda la poblacion no se destaca sobre toda la poblacion] [La sensibilidad se calculaba sobre los 88 puestos de Bucaramanga, pero el reporte destacaba el maximo global: un recinto penitenciario de 96 votos. Es el mismo error que el top de oportunidad que llenaban las carceles] [El indice se calcula sobre el conjunto completo —necesita poblacion para el percentil— pero al destacar se elige solo dentro de los objetivos del reporte. Destacar el maximo global responde a una pregunta que nadie hizo. Dos preguntas distintas, dos poblaciones distintas.]

## NOMBRAR UN MODELO POR LO QUE ES

- [No llamar «entropia» a una formula de decision fija] [La reduccion de incertidumbre del motor de senalizacion se calcula con `base_senal x ajuste_triangular`; presentarla como entropia de Shannon seria el mismo error que presentar un umbral fijo como hallazgo] [Todo porcentaje que salga de una formula lleva al lado la frase «modelo de decision declarado, no una medicion». Si el nombre necesita una metáfora para sonar cientifico, el indicador no lo es.]

- [Un umbral fijo no distingue nada, se llame como se llame] [Cinco apariciones del mismo error: Benford al 5 %, umbral de red al 25 %, grafo completo, volatilidad de partido lider al 97 %, clase media con desaparecidas] [Todo corte sale de un percentil de la distribucion observada, y el percentil se publica junto al corte. Si alguien propone un valor fijo —25 %, 5 %, 80 %— la pregunta es: contra que distribucion lo mediste.]

## LA BUSQUEDA TAMBIEN TIENE QUE FUNCIONAR

- [Una memoria que no se puede consultar con tildes es una memoria a medias] [`buscar_leccion("metrica")` devolvia 0 porque el registro dice «métrica»; `buscar_leccion("entropía")` devolvia 0 porque no habia ninguna entrada] [Normalizar tildes y mayusculas en la busqueda, y probar la consulta con las dos formas. Si la memoria no responde a la pregunta tal como se escribe, el fallo es de la memoria, no de quien pregunta.]

## UNA PRUEBA INESTABLE ES PEOR QUE NINGUNA PRUEBA

- [Un limite de rendimiento ajustado convierte la prueba en inestable, y una prueba inestable se acaba ignorando] [«drift bajo 2 s» fallo con 2,05 s; tres corridas dieron 1,05, 1,40 y 1,34 s. El limite no medía el codigo, medía la carga de la maquina] [Las pruebas de rendimiento llevan margen y declaran que detectan regresiones catastroficas. Para medir rendimiento fino hay un benchmark aparte, no la suite de correccion.]
