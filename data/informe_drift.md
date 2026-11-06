# Deriva entre elecciones · Asamblea 2023 → Cámara 2026

**Regla:** el drift se mide contra el propio departamento. Un municipio que se mueve como todos no deriva: tiende.

## Una metrica que no se pudo calcular

**Porcentaje de puestos que cambiaron de partido lider** — no computable.

Los universos de partida no se solapan: 16 codigos en Asamblea 2023 y 68 en Cámara 2026, con solo 4 comunes. El numero resultante es 97 % en todos los pares y no mide volatilidad del electorado.

*Sustituto:* Se mide el cambio de cuota del ganador, que no necesita identidad de partido y responde a la misma pregunta: el primero domina mas o menos que antes.

## Umbrales medidos

Cada metrica tiene su distribucion, asi que cada una tiene su corte. Se marcan los **9 municipios** mas alejados en cada metrica (percentil 90), no los que superan un valor fijo.

| Metrica | Unidad | Corte |
|---|---|---:|
| Cuota del ganador | puntos porcentuales | 19.35 |
| Tasa de perdida | puntos porcentuales | 25.57 |
| Concentracion | indice Herfindahl | 0.1075 |

**Municipios marcados en al menos una metrica: 18 de 87.**

## Las tres metricas por municipio

| Municipio | Puestos | Cuota ganador | Perdida | Concentracion | Marcas |
|---|---:|---:|---:|---:|---|
| SAN JOAQUIN | 1 | +39.32 pp | -26.53 pp | +0.2613 | drift_cuota, drift_perdida, drift_hhi |
| JORDAN | 3 | +19.35 pp | -38.08 pp | +0.1256 | drift_cuota, drift_perdida, drift_hhi |
| MACARAVITA | 1 | +26.66 pp | -13.83 pp | +0.1622 | drift_cuota, drift_hhi |
| CONFINES | 2 | +25.04 pp | -24.21 pp | +0.1491 | drift_cuota, drift_hhi |
| MOLAGAVITA | 12 | +22.38 pp | -17.33 pp | +0.1503 | drift_cuota, drift_hhi |
| TONA | 4 | -20.25 pp | -11.78 pp | -0.1257 | drift_cuota, drift_hhi |
| OIBA | 5 | +19.81 pp | -24.04 pp | +0.1075 | drift_cuota, drift_hhi |
| MALAGA | 9 | +21.63 pp | -16.14 pp | +0.1063 | drift_cuota |
| PARAMO | 1 | +21.21 pp | -20.98 pp | +0.0984 | drift_cuota |
| GUAPOTA | 2 | +17.44 pp | -21.03 pp | +0.1542 | drift_hhi |
| SURATA | 5 | +17.40 pp | -16.63 pp | +0.1226 | drift_hhi |
| VALLE DE SAN JOSE | 4 | +13.40 pp | -25.57 pp | +0.0768 | drift_perdida |
| MOGOTES | 8 | +8.10 pp | -26.96 pp | +0.0706 | drift_perdida |
| LOS SANTOS | 6 | +7.92 pp | -26.09 pp | +0.0602 | drift_perdida |
| LANDAZURI | 9 | +5.09 pp | -26.40 pp | +0.0319 | drift_perdida |

## Hipotesis para los municipios marcados

### SAN JOAQUIN

Marcas: **drift_cuota, drift_perdida, drift_hhi**.

- **H1 · Cambio de electorado** — `NO VERIFICABLE`
  *El vault no contiene datos demograficos ni de poblacion.*
- **H2 · Cambio de codificacion** — `VERIFICABLE`
  15 listas en 2023 frente a 12 en 2026. El numero de listas cambio: eso basta para mover la concentracion sin que cambie un solo voto.
- **H3 · Efecto de coalicion** — `PARCIAL`
  Se detecta la palabra «coalicion» en los nombres de partido, no la estructura real de la alianza.
- **H4 · Efecto de candidato** — `NO VERIFICABLE`
  *El archivo de candidatos solo cubre 2026; no hay enlace con 2023.*

### JORDAN

Marcas: **drift_cuota, drift_perdida, drift_hhi**.

- **H1 · Cambio de electorado** — `NO VERIFICABLE`
  *El vault no contiene datos demograficos ni de poblacion.*
- **H2 · Cambio de codificacion** — `VERIFICABLE`
  12 listas en 2023 frente a 9 en 2026. El numero de listas cambio: eso basta para mover la concentracion sin que cambie un solo voto.
- **H3 · Efecto de coalicion** — `PARCIAL`
  Se detecta la palabra «coalicion» en los nombres de partido, no la estructura real de la alianza.
- **H4 · Efecto de candidato** — `NO VERIFICABLE`
  *El archivo de candidatos solo cubre 2026; no hay enlace con 2023.*

### MACARAVITA

Marcas: **drift_cuota, drift_hhi**.

- **H1 · Cambio de electorado** — `NO VERIFICABLE`
  *El vault no contiene datos demograficos ni de poblacion.*
- **H2 · Cambio de codificacion** — `VERIFICABLE`
  15 listas en 2023 frente a 11 en 2026. El numero de listas cambio: eso basta para mover la concentracion sin que cambie un solo voto.
- **H3 · Efecto de coalicion** — `PARCIAL`
  Se detecta la palabra «coalicion» en los nombres de partido, no la estructura real de la alianza.
- **H4 · Efecto de candidato** — `NO VERIFICABLE`
  *El archivo de candidatos solo cubre 2026; no hay enlace con 2023.*

### CONFINES

Marcas: **drift_cuota, drift_hhi**.

- **H1 · Cambio de electorado** — `NO VERIFICABLE`
  *El vault no contiene datos demograficos ni de poblacion.*
- **H2 · Cambio de codificacion** — `VERIFICABLE`
  16 listas en 2023 frente a 12 en 2026. El numero de listas cambio: eso basta para mover la concentracion sin que cambie un solo voto.
- **H3 · Efecto de coalicion** — `PARCIAL`
  Se detecta la palabra «coalicion» en los nombres de partido, no la estructura real de la alianza.
- **H4 · Efecto de candidato** — `NO VERIFICABLE`
  *El archivo de candidatos solo cubre 2026; no hay enlace con 2023.*

### MOLAGAVITA

Marcas: **drift_cuota, drift_hhi**.

- **H1 · Cambio de electorado** — `NO VERIFICABLE`
  *El vault no contiene datos demograficos ni de poblacion.*
- **H2 · Cambio de codificacion** — `VERIFICABLE`
  11 listas en 2023 frente a 8 en 2026. El numero de listas cambio: eso basta para mover la concentracion sin que cambie un solo voto.
- **H3 · Efecto de coalicion** — `PARCIAL`
  Se detecta la palabra «coalicion» en los nombres de partido, no la estructura real de la alianza.
- **H4 · Efecto de candidato** — `NO VERIFICABLE`
  *El archivo de candidatos solo cubre 2026; no hay enlace con 2023.*

## Lo que este informe no puede atribuir al electorado

- Se compara Asamblea 2023 con Cámara 2026. Ambas son departamentales, pero una elige corporacion local y la otra nacional: el electorado no es el mismo y el numero de listas tampoco.
- **H1 no verificable:** no hay datos demograficos en el vault.
- **H4 no verificable:** no hay enlace de candidatos entre 2023 y 2026.
- **H3 parcial:** se detecta la palabra «coalicion», no la estructura.

Un municipio marcado no es un municipio con un electorado distinto. Es un municipio que se movio distinto, y no se sabe por que.
