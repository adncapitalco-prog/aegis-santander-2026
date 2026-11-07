# DECISION LOG · AEGIS-POLITICA

**Formato:** `- [FECHA] [DECISIÓN] [RAZÓN] [ALTERNATIVAS DESCARTADAS]`

**Append-only.** Una decisión superada se marca `SUPERADA` en una entrada
nueva; no se borra la original.

---

## ARQUITECTURA DE REPORTES

- [2026-11-04] [Usar ContratoReporte como única fuente entre datos y renderizado] [El renderizador debe poder dibujar cualquier dominio sin conocerlo] [Pasar un dict crudo · renderizar directamente en el adaptador]
- [2026-11-04] [Los adaptadores devuelven markdown, no SVG] [Solo el nivel piloto necesita SVG; técnico y Feynman son texto] [Un solo formato para los tres niveles]
- [2026-11-04] [Los nombres de los 5 puestos viajan en `puestos_objetivo` del contrato] [El renderizador no puede contener nombres de dominio] [Hardcodear en renderizador · tabla por puesto en el adaptador]
- [2026-11-04] [Acortar nombres con reglas genéricas (RUIDO_INICIAL, RUIDO_FINAL, CONECTORES)] [Ningún nombre completo cabe en el nodo y una tabla por puesto vuelve a hardcodear] [Alias manual por puesto · truncar con puntos suspensivos]
- [2026-11-05] [Añadir `prioridades: List[Dict]` al contrato en vez de tres campos escalares] [El reporte cubre 5 puestos con 5 diagnósticos; un escalar pierde información] [Resumir en un solo nivel · no reportar prioridad]

## MOTOR PREDICTIVO Y RED

- [2026-11-05] [Sustituir la alerta Benford por desviación de red] [Benford aplicado a 314 candidatos con 12 votos de media es ruido; marcó 25 de 825 y al menos uno era falso positivo] [Mantener Benford · umbral más alto · eliminar la alerta sin sustituto]
- [2026-11-05] [Umbral de red calibrado por percentil 90, no fijo] [Con umbral fijo de 25 % se marcaban 34 de 88 puestos (39 %)] [Umbral fijo 25 % · 50 % · media + 2 desviaciones]
- [2026-11-05] [Grafo disperso: solo comuna o afinidad, tope de 12 vecinos] [La versión que conectaba todo par del municipio dio densidad 1,0 y marcó 88 de 88] [Grafo completo · k-vecinos más cercanos · umbral de correlación]
- [2026-11-05] [Desviación ajustada por tamaño (z de la proporción)] [La desviación relativa correlaciona −0,34 con el volumen y vaciaba el cuadrante crítico de la matriz] [Desviación relativa · cuota bruta · rango intercuartílico]
- [2026-11-05] [Matriz de prioridad 2x2 con p80 de recuperables y p90 del z] [Cruza volumen y anomalía; separa Café Madrid (N1) de La Capilla (N4)] [Solo volumen · solo anomalía · ranking lineal]

## DRIFT Y PERFILES

- [2026-11-06] [Sustituir «cuota del ganador» por «volatilidad de la clase media»] [Cuota y HHI correlacionan +0,888: medían lo mismo] [Eliminar una de las tres · dejar solo HHI]
- [2026-11-06] [Sumar solo los partidos de clase media que existen en ambos años] [Incluir los desaparecidos sube la correlación con HHI a +0,344 y pone el mínimo en 7,38 pp] [Todas las partidas · solo las de 2023]
- [2026-11-06] [Declarar NO CALCULABLE la resiliencia cuando el líder de 2023 no compite en 2026] [Un cero afirmaría que el partido desapareció del electorado; lo que desapareció fue la lista] [Cero · media del municipio · excluir el municipio]
- [2026-11-06] [Renunciar a «volatilidad de partido líder» como métrica comparativa] [Da 97 % en todos los pares: 16 códigos en Asamblea 2023, 68 en Cámara 2026, 4 comunes] [Restringir a partidos comunes · comparar alcaldía contra alcaldía]

## DATOS E INTEGRIDAD

- [2026-11-05] [Unir partidos por código entero, nunca por nombre] [Los nombres difieren en mayúsculas y tildes entre años; unir por nombre dio 87 municipios mal clasificados] [Normalizar nombres · fuzzy matching]
- [2026-11-05] [Rutas de datos como parámetros, no constantes] [Una ruta absoluta del vault en `_prioridades` hizo que la nube mostrara cifras viejas durante tres despliegues] [Variable de entorno · detectar por `__file__`]
- [2026-11-05] [Precalcular agregados en sidecar JSON en vez de optimizar la lectura] [`_sin_nombre` tardaba 1,19 s por reporte; el sidecar de 184 bytes lo deja en 0,011 s (109x)] [pyarrow sobre parquet (0,59 s) · caché en memoria · polars]
- [2026-11-05] [Encoding cp1252 para los archivos de la Registraduría] [Los TXT fallan al decodificar como UTF-8 en los bytes 859 y 37] [latin-1 · utf-8 con errors=replace]

## GOBIERNO

- [2026-11-05] [Registrar las deudas forenses en un archivo propio y declararlas en los tres niveles] [DF-001 (1.564 votos) no se puede resolver; elegir una cifra y callar la otra sería peor] [Elegir la del vault · elegir la oficial · omitir la discrepancia]
- [2026-11-06] [Rechazar «ADN cultural» y «vectores meméticos»] [No hay un solo dato cultural en el vault; serían votos renombrados y se leerían como antropología] [Perfiles de comportamiento electoral nombrados por lo que miden]
- [2026-11-06] [No escalar a otro departamento hasta recalibrar todos los percentiles] [Un p80 de 87 municipios no significa lo mismo que un p80 de 125] [Copiar umbrales · recalibrar solo algunos]

## SUPERADAS

- [2026-11-04] [Fondo opaco en los gráficos para evitar texto oscuro sobre tema oscuro] [El problema real era el color del texto, no la transparencia] [Transparente con texto adaptativo al tema] → **SUPERADA 2026-11-04** por la entrada de tema claro.
- [2026-11-05] [Declarar que Pacto Histórico tiene dos cifras contradictorias: 142.335 y 157.017] [Comparación errónea: 3096 es Cámara y 3063 es Senado] [Son listas distintas; no hay contradicción] → **SUPERADA 2026-11-05** tras la investigación DF-002.
- [2026-11-06] [Indice de sensibilidad por rango percentil, no por min-max] [Min-max aplasta el conjunto cuando hay un outlier; el percentil reparte la escala y no depende de su magnitud] [Min-max · z-score · distancia a la media]
- [2026-11-06] [Declarar la reduccion de entropia como modelo, no como medicion] [Se calcula con `base_senal x ajuste_triangular`; presentarla como entropia de Shannon seria el mismo error que presentar un umbral fijo como hallazgo] [Llamarla «entropia» sin declarar · omitir el porcentaje]
- [2026-11-06] [Destacar la senal solo entre los objetivos del reporte, no entre los 825 puestos] [La sensibilidad se calcula sobre todo el municipio, pero destacar un recinto penitenciario de 96 votos repite el error del top de oportunidad] [Destacar el maximo global · destacar por volumen]
- [2026-11-06] [Umbral de la prueba de rendimiento de drift en 3 s, no en 2] [Medido 1,05 · 1,40 · 1,34 s en tres corridas; un limite ajustado vuelve la prueba inestable y una prueba inestable se ignora] [Prologar la prueba · quitarla]
