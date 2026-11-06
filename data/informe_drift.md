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
| Volatilidad de la clase media | puntos porcentuales | 13.78 |
| Tasa de perdida | puntos porcentuales | 25.57 |
| Concentracion | indice Herfindahl | 0.1075 |

**Municipios marcados en al menos una metrica: 25 de 87.**

## Las tres metricas por municipio

| Municipio | Puestos | Clase media | Perdida | Concentracion | Marcas |
|---|---:|---:|---:|---:|---|
| JORDAN | 3 | +3.92 pp | -38.08 pp | +0.1256 | drift_perdida, drift_hhi |
| SAN JOAQUIN | 1 | +0.35 pp | -26.53 pp | +0.2613 | drift_perdida, drift_hhi |
| BARICHARA | 1 | +31.64 pp | -18.33 pp | -0.0644 | drift_clase_media |
| EL GUACAMAYO | 2 | +29.12 pp | -20.44 pp | +0.0549 | drift_clase_media |
| VETAS | 1 | +23.33 pp | -13.61 pp | +0.0514 | drift_clase_media |
| PIEDECUESTA | 42 | +23.32 pp | -22.64 pp | +0.0819 | drift_clase_media |
| CERRITO | 4 | +21.91 pp | -13.24 pp | -0.0116 | drift_clase_media |
| RIONEGRO | 27 | +17.05 pp | -21.35 pp | +0.0169 | drift_clase_media |
| CEPITA | 8 | +16.06 pp | -13.30 pp | +0.0784 | drift_clase_media |
| MATANZA | 6 | +14.31 pp | -17.85 pp | +0.0444 | drift_clase_media |
| ALBANIA | 7 | +13.78 pp | -22.18 pp | +0.0011 | drift_clase_media |
| TONA | 4 | +10.66 pp | -11.78 pp | -0.1257 | drift_hhi |
| CONFINES | 2 | +10.33 pp | -24.21 pp | +0.1491 | drift_hhi |
| LOS SANTOS | 6 | +10.06 pp | -26.09 pp | +0.0602 | drift_perdida |
| SURATA | 5 | +7.52 pp | -16.63 pp | +0.1226 | drift_hhi |

## Hipotesis para los municipios marcados

### JORDAN

Marcas: **drift_perdida, drift_hhi**.

- **H1 · Cambio de electorado** — `NO VERIFICABLE`
  *El vault no contiene datos demograficos ni de poblacion.*
- **H2 · Cambio de codificacion** — `VERIFICABLE`
  12 listas en 2023 frente a 9 en 2026. El numero de listas cambio: eso basta para mover la concentracion sin que cambie un solo voto.
- **H3 · Efecto de coalicion** — `PARCIAL`
  Se detecta la palabra «coalicion» en los nombres de partido, no la estructura real de la alianza.
- **H4 · Efecto de candidato** — `NO VERIFICABLE`
  *El archivo de candidatos solo cubre 2026; no hay enlace con 2023.*

### SAN JOAQUIN

Marcas: **drift_perdida, drift_hhi**.

- **H1 · Cambio de electorado** — `NO VERIFICABLE`
  *El vault no contiene datos demograficos ni de poblacion.*
- **H2 · Cambio de codificacion** — `VERIFICABLE`
  15 listas en 2023 frente a 12 en 2026. El numero de listas cambio: eso basta para mover la concentracion sin que cambie un solo voto.
- **H3 · Efecto de coalicion** — `PARCIAL`
  Se detecta la palabra «coalicion» en los nombres de partido, no la estructura real de la alianza.
- **H4 · Efecto de candidato** — `NO VERIFICABLE`
  *El archivo de candidatos solo cubre 2026; no hay enlace con 2023.*

### BARICHARA

Marcas: **drift_clase_media**.

- **H1 · Cambio de electorado** — `NO VERIFICABLE`
  *El vault no contiene datos demograficos ni de poblacion.*
- **H2 · Cambio de codificacion** — `VERIFICABLE`
  16 listas en 2023 frente a 18 en 2026. El numero de listas cambio: eso basta para mover la concentracion sin que cambie un solo voto.
- **H3 · Efecto de coalicion** — `PARCIAL`
  Se detecta la palabra «coalicion» en los nombres de partido, no la estructura real de la alianza.
- **H4 · Efecto de candidato** — `NO VERIFICABLE`
  *El archivo de candidatos solo cubre 2026; no hay enlace con 2023.*

### EL GUACAMAYO

Marcas: **drift_clase_media**.

- **H1 · Cambio de electorado** — `NO VERIFICABLE`
  *El vault no contiene datos demograficos ni de poblacion.*
- **H2 · Cambio de codificacion** — `VERIFICABLE`
  12 listas en 2023 frente a 10 en 2026. El numero de listas cambio: eso basta para mover la concentracion sin que cambie un solo voto.
- **H3 · Efecto de coalicion** — `PARCIAL`
  Se detecta la palabra «coalicion» en los nombres de partido, no la estructura real de la alianza.
- **H4 · Efecto de candidato** — `NO VERIFICABLE`
  *El archivo de candidatos solo cubre 2026; no hay enlace con 2023.*

### VETAS

Marcas: **drift_clase_media**.

- **H1 · Cambio de electorado** — `NO VERIFICABLE`
  *El vault no contiene datos demograficos ni de poblacion.*
- **H2 · Cambio de codificacion** — `VERIFICABLE`
  15 listas en 2023 frente a 11 en 2026. El numero de listas cambio: eso basta para mover la concentracion sin que cambie un solo voto.
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
