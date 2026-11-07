# AEGIS-INTELLECT - Dashboard Estrategico Santander

## Despliegue en Streamlit Cloud

1. Sube esta carpeta completa a un repositorio de GitHub.
2. En share.streamlit.io crea una app apuntando a `app.py`.
3. En Secrets del panel de Streamlit define:

```toml
AEGIS_DASH_USER = "analista"
AEGIS_DASH_PASSWORD_SHA256 = "<hash de 64 caracteres>"
```

4. Genera el hash de tu clave:

```
python -c "import hashlib;print(hashlib.sha256('TuClave'.encode()).hexdigest())"
```

Sin esas credenciales la app no abre (H5: fail-closed).

## Estructura

```
app.py                                    dashboard, 5 pestanas
requirements.txt                          dependencias fijadas
data/detalle_candidatos_santander.zip     300.734 filas
data/anomalias_y_clusters.csv             825 puestos
data/atlas_santander_maestro.csv          825 puestos
data/atlas_santander_partidos.csv         4.125 filas
.streamlit/config.toml                    tema
```

## Portabilidad

La app busca los datos en `data/`, junto a `app.py`.
Si no los encuentra, cae a la ruta absoluta del vault.
El mismo archivo corre en local y en la nube.
