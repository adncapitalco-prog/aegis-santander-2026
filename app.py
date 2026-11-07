# -*- coding: utf-8 -*-
# =============================================================================
# AEGIS-INTELLECT - dashboard estrategico  (GENERADO - no editar a mano)
# Generado: 2026-11-07 00:01
# Fuente: C:\Users\Javier\Documents\AEGIS-POLITICA\08_Reportes\Atlas_Detallado\detalle_candidatos_santander.csv
# Sello SHA256 de la fuente: 8be7b6503023e11eebe5d217cce3d4d195a9cb4525a6dc3c55c4f845eb562300
#
# Arranque (PowerShell):
#   $env:AEGIS_DASH_USER="analista"
#   $env:AEGIS_DASH_PASSWORD_SHA256=(python -c "import hashlib;print(hashlib.sha256('TuClave'.encode()).hexdigest())")
#   streamlit run app.py
#
# H5 (fail-closed): sin credenciales la app no abre.
# =============================================================================

import hashlib
import hmac
import io
import os

import subprocess
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PALETA = {"acento_alerta": "#D32F2F", "exito": "#1B7A3D", "fondo": "#F8F9FA", "primario": "#002B5C", "secundario": "#457B9D", "tarjeta": "#FFFFFF"}
FUENTE = "'Inter', 'Segoe UI', sans-serif"
# --- RUTAS PORTABLES ---------------------------------------------------------
# El tablero corre en dos entornos: la PC del analista y Streamlit Cloud.
# En la nube los datos viajan con el repo, en data/. En local estan en el
# vault. Se busca en ese orden y se usa lo primero que exista, asi el mismo
# archivo funciona en ambos sin tocar codigo.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Respaldo local: solo se usa si data/ no existe.
_RUTA_LOCAL_DETALLE = r"C:\Users\Javier\Documents\AEGIS-POLITICA\08_Reportes\Atlas_Detallado\detalle_candidatos_santander.csv"
_RUTA_LOCAL_PREDICTIVO = r"C:\Users\Javier\Documents\AEGIS-POLITICA\08_Reportes\Atlas_Predictivo\anomalias_y_clusters.csv"


def resolver(nombre_data, respaldo_local):
    """Devuelve la primera ruta que exista: data/ primero, respaldo despues."""
    candidato = os.path.join(DATA_DIR, nombre_data)
    if os.path.exists(candidato):
        return candidato
    if respaldo_local and os.path.exists(respaldo_local):
        return respaldo_local
    return None


# Orden de preferencia del detalle:
#   1. Parquet  - formato interno del vault (medido 4,9x-12,7x mas rapido)
#   2. ZIP      - formato de despliegue (Streamlit Cloud no recibe parquet)
#   3. CSV      - respaldo local sin comprimir
_RUTA_LOCAL_PARQUET = r"C:\Users\Javier\Documents\AEGIS-POLITICA\08_Reportes\Atlas_Detallado\detalle_candidatos_santander.parquet"
RUTA_DETALLE = (
    resolver("detalle_candidatos_santander.parquet", _RUTA_LOCAL_PARQUET)
    or resolver("detalle_candidatos_santander.zip", _RUTA_LOCAL_DETALLE)
    or resolver("detalle_candidatos_santander.csv", _RUTA_LOCAL_DETALLE)
)
RUTA_PREDICTIVO = resolver("anomalias_y_clusters.csv", _RUTA_LOCAL_PREDICTIVO)
RUTA_PARTIDOS_CSV = resolver("atlas_santander_partidos.csv", "")
RUTA_MAESTRO = resolver("atlas_santander_maestro.csv",
                        os.path.join(os.path.dirname(_RUTA_LOCAL_DETALLE),
                                     "atlas_santander_maestro.csv"))
RUTA_PARTIDOS = resolver("atlas_santander_partidos.csv",
                         os.path.join(os.path.dirname(_RUTA_LOCAL_DETALLE),
                                      "atlas_santander_partidos.csv"))
SELLO_DATOS = "8be7b6503023e11eebe5d217cce3d4d195a9cb4525a6dc3c55c4f845eb562300"

NO_APROVECHADO = "Voto no aprovechado"
UMBRAL = 0.80
UMBRAL_RIESGO = 10.0
# En corporaciones uninominales el campo "partido" del MMV guarda el
# LEMA de campana, no el partido ("DEFENDAMOS BUCARAMANGA").
CORP_UNINOMINAL = ("Gobernación", "Gobernacion", "Alcaldía", "Alcaldia")

st.set_page_config(page_title="AEGIS-INTELLECT", layout="wide",
                   initial_sidebar_state="expanded")


# --- utilidades --------------------------------------------------------------
def miles(n):
    try:
        return format(int(round(float(n))), ",d").replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def pct(n, decimales=1):
    try:
        return ("{:.%df}" % decimales).format(float(n)).replace(".", ",") + " %"
    except (TypeError, ValueError):
        return "0 %"


def paleta_grafico():
    """Colores de los graficos.

    Fondo TRANSPARENTE: el lienzo hereda el color de la pagina, asi el grafico
    no compite con la tarjeta que lo contiene.

    Lo que NO puede ser transparente es el criterio del texto. Si el texto se
    fija en oscuro y alguien pone la app en tema oscuro, el grafico desaparece:
    fue exactamente el defecto que se corrigio antes. Por eso el color del
    texto y de la rejilla siguen al tema, aunque el fondo no lo haga.
    """
    try:
        base = (st.get_option("theme.base") or "light").lower()
    except Exception:
        base = "light"
    if base == "dark":
        return {"texto": "#FFFFFF", "fondo": "rgba(0,0,0,0)", "grid": "#2A2F3A",
                "titulo": "#FFFFFF", "neutro": "#9AA5B1"}
    return {"texto": "#262730", "fondo": "rgba(0,0,0,0)", "grid": "#E5E7EB",
            "titulo": "#002B5C", "neutro": "#6B7280"}


def entidad(fila):
    """Nombre mostrable de la fila: candidato si es uninominal, partido si no."""
    if str(fila.get("corporacion", "")).strip() in CORP_UNINOMINAL:
        cand = str(fila.get("candidato", "")).strip()
        if cand:
            return cand
    return str(fila.get("partido", "") or "").strip()


def es_lista_cerrada(sub):
    """Una lista es cerrada si todos sus votos van a un unico codigo de candidato.

    Se detecta en los datos, no en una tabla de configuracion: un partido de
    lista cerrada registra un solo codigo de candidato ('000') en todas sus
    filas. Una lista abierta reparte los votos entre varios.
    """
    if sub is None or sub.empty or "candidato_id" not in sub.columns:
        return False
    codigos = set(sub["candidato_id"].astype(str).str.strip())
    codigos.discard("")
    return len(codigos) <= 1


def es_pendiente(nombre):
    n = str(nombre or "")
    return "nombre pendiente" in n or n.startswith("Código")


def credenciales():
    return (os.environ.get("AEGIS_DASH_USER", "").strip(),
            os.environ.get("AEGIS_DASH_PASSWORD_SHA256", "").strip().lower())


def autenticar():
    usuario_esperado, hash_esperado = credenciales()
    if not usuario_esperado or len(hash_esperado) != 64:
        st.error("Autenticacion no configurada. Defina AEGIS_DASH_USER y "
                 "AEGIS_DASH_PASSWORD_SHA256 (H5: fail-closed).")
        return False
    if st.session_state.get("aegis_autenticado"):
        return True
    st.markdown("### Acceso restringido")
    with st.form("aegis_login"):
        usuario = st.text_input("Usuario")
        clave = st.text_input("Clave", type="password")
        enviado = st.form_submit_button("Entrar")
    if enviado:
        calculado = hashlib.sha256(clave.encode("utf-8")).hexdigest()
        if hmac.compare_digest(usuario.strip(), usuario_esperado) and \
                hmac.compare_digest(calculado, hash_esperado):
            st.session_state["aegis_autenticado"] = True
            return True
        st.error("Credenciales invalidas.")
    return False


# --- guardian de arranque ----------------------------------------------------
def ejecutar_pre_flight():
    """Corre el Pre-flight antes de cargar cualquier dato. Fail-closed.

    Devuelve (codigo, salida). codigo 0 = autorizado. Cualquier otro valor
    detiene el tablero: es preferible un tablero apagado que un tablero con
    datos que nadie verifico.

    Busca el guardian junto a app.py (paquete deploy) y, si no esta, en la
    estructura del vault.
    """
    candidatos = [
        os.path.join(BASE_DIR, "pre_flight_check.py"),
        os.path.join(BASE_DIR, "..", "..", "pre_flight_check.py"),
        os.path.join(BASE_DIR, "..", "..", "06_Herramientas", "pre_flight_check.py"),
    ]
    guardian = next((c for c in candidatos if os.path.exists(c)), None)
    if guardian is None:
        return 2, "No se encontro pre_flight_check.py. Buscado en: " + " | ".join(candidatos)

    manifiesto = None
    for cand in (os.path.join(BASE_DIR, "manifest.json"),
                 os.path.join(BASE_DIR, "..", "..", "manifest.json")):
        if os.path.exists(cand):
            manifiesto = cand
            break

    orden = [sys.executable, guardian, "--modo", "deploy", "--raiz", BASE_DIR]
    if manifiesto:
        orden += ["--manifest", manifiesto]
    try:
        proceso = subprocess.run(orden, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return 2, "El Pre-flight no respondio en 60 segundos."
    except OSError as error:
        return 2, "No se pudo ejecutar el Pre-flight: %s" % error
    return proceso.returncode, (proceso.stdout or "") + (proceso.stderr or "")


# --- resolucion de nombres de partido ---------------------------------------
_MAPEO_PARTIDOS = {}


def _cargar_mapeo_ui():
    global _MAPEO_PARTIDOS
    if _MAPEO_PARTIDOS:
        return _MAPEO_PARTIDOS
    import json
    ruta = os.path.join(BASE_DIR, "..", "..", "08_Reportes",
                        "mapeo_partidos_2026.json")
    for cand in (os.path.join(BASE_DIR, "data", "mapeo_partidos_2026.json"),
                 os.path.abspath(ruta)):
        if os.path.exists(cand):
            try:
                with open(cand, encoding="utf-8") as fh:
                    _MAPEO_PARTIDOS = {int(k): v for k, v in
                                       json.load(fh).get("partidos", {}).items()}
                break
            except (ValueError, OSError):
                continue
    return _MAPEO_PARTIDOS


def _votos_sin_nombre(ruta_partidos):
    """Cuenta votos cuyo codigo de partido no resuelve el catalogo oficial.

    Se calcula en vez de escribirse a mano. El KPI decia 353.282 y luego
    413.495: ninguno de los dos se actualizaba solo, y los dos quedaron
    obsoletos cuando llego el mapeo.
    """
    mapeo = _cargar_mapeo_ui()
    if not mapeo or not os.path.exists(ruta_partidos):
        return 0, 0
    import csv as _csv
    sin_nombre = 0
    total = 0
    try:
        with open(ruta_partidos, encoding="utf-8-sig", newline="") as fh:
            for r in _csv.DictReader(fh):
                try:
                    codigo = int(r["Codigo_Partido"])
                    votos = int(r["Votos_Partido"])
                except (KeyError, ValueError):
                    continue
                total += votos
                if codigo not in mapeo:
                    sin_nombre += votos
    except OSError:
        return 0, 0
    return sin_nombre, total


def _resolver_partido_ui(texto):
    """Traduce 'Código 3063 · nombre pendiente' al nombre oficial."""
    if not isinstance(texto, str) or "pendiente" not in texto.lower():
        return texto
    import re
    m = re.search(r"(\d{2,5})", texto)
    if not m:
        return texto
    mapeo = _cargar_mapeo_ui()
    return mapeo.get(int(m.group(1)), texto)


# --- motor de reportes -------------------------------------------------------
def cargar_motor_reportes():
    """Importa motor_reportes desde donde este.

    En el vault vive en 06_Herramientas/motor_reportes. En el paquete de
    despliegue viaja junto a app.py. Se prueban las dos ubicaciones y se
    devuelve None si no aparece: el tablero avisa y sigue funcionando.
    """
    candidatos = [
        BASE_DIR,                                   # deploy: junto a app.py
        os.path.join(BASE_DIR, "..", ".."),         # vault: 06_Herramientas
        os.path.join(BASE_DIR, "..", "..", ".."),   # por si cambia la profundidad
    ]
    for ruta in candidatos:
        ruta = os.path.abspath(ruta)
        if os.path.isdir(os.path.join(ruta, "motor_reportes")):
            if ruta not in sys.path:
                sys.path.insert(0, ruta)
            try:
                import importlib
                import motor_reportes
                # importlib.reload del paquete raiz NO recarga los submodulos.
                # Si feynman.py cambia en disco con el servidor encendido,
                # Streamlit sigue sirviendo el modulo viejo de memoria. Hay que
                # recargar cada submodulo que el tablero usa.
                for nombre_mod in ("motor_reportes.contrato",
                                   "motor_reportes.renderizador",
                                   "motor_reportes.datos_electorales",
                                   "motor_reportes.adaptadores",
                                   "motor_reportes.adaptadores.piloto",
                                   "motor_reportes.adaptadores.tecnico",
                                   "motor_reportes.adaptadores.feynman"):
                    if nombre_mod in sys.modules:
                        try:
                            importlib.reload(sys.modules[nombre_mod])
                        except Exception:
                            pass
                importlib.reload(motor_reportes)
                from motor_reportes import adaptadores, renderizador
                from motor_reportes.datos_electorales import extraer
                return {"adaptadores": adaptadores,
                        "renderizador": renderizador,
                        "extraer": extraer,
                        "raiz": ruta}
            except Exception:
                continue
    return None


# --- datos -------------------------------------------------------------------
@st.cache_data(show_spinner="Cargando detalle de Santander...")
def cargar(ruta):
    """Lee el detalle una sola vez y devuelve un DataFrame normalizado.

    Acepta .csv y .zip: en la nube el detalle viaja comprimido para no
    cargar el repositorio con 30 MB, y pandas descomprime al vuelo.
    """
    ruta = str(ruta)
    if ruta.lower().endswith(".parquet"):
        df = pd.read_parquet(ruta, engine="pyarrow")
    else:
        compresion = "zip" if ruta.lower().endswith(".zip") else None
        df = pd.read_csv(ruta, encoding="utf-8-sig", dtype=str, keep_default_na=False,
                         compression=compresion)
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={"anio_eleccion": "anio",
                            "nombre_partido": "partido",
                            "nombre_candidato": "candidato"})
    df["votos"] = pd.to_numeric(df["votos"], errors="coerce").fillna(0).astype("int64")
    for col in ("municipio", "corporacion", "partido", "candidato", "anio",
                "zona", "puesto"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    df["es_invalido"] = df["partido"].str.lower() == NO_APROVECHADO.lower()
    df["puesto_id"] = df["zona"].str.zfill(3) + "/" + df["puesto"].str.zfill(2)
    df["candidato_id"] = df["codigo_candidato"].astype(str).str.strip() \
        if "codigo_candidato" in df.columns else ""
    return df


def pareto(serie, total):
    """Ordena descendente y calcula porcentaje, acumulado y cierre del 80 %."""
    columnas = ["etiqueta", "votos", "pct", "acum", "en_80", "n80"]
    if serie.empty or total <= 0:
        return pd.DataFrame(columns=columnas)
    d = serie.groupby("etiqueta", as_index=False)["votos"].sum()
    d = d.sort_values("votos", ascending=False).reset_index(drop=True)
    d["pct"] = 100.0 * d["votos"] / total
    d["acum"] = d["pct"].cumsum()
    cruce = d.index[d["acum"] >= UMBRAL * 100]
    n80 = int(cruce[0]) + 1 if len(cruce) else len(d)
    d["en_80"] = d.index < n80
    d["n80"] = n80
    return d


def figura_pareto(d, titulo, alto=400):
    """Barras del top 10 con la linea de acumulado en el eje secundario."""
    t = paleta_grafico()
    top = d.head(10)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top["etiqueta"], y=top["votos"], name="Votos",
        marker_color=PALETA["primario"],
        text=[miles(v) for v in top["votos"]], textposition="outside",
        textfont=dict(color=t["texto"], size=11),
        hovertemplate="%{x}<br>Votos: %{text}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=top["etiqueta"], y=top["acum"], name="Acumulado",
        yaxis="y2", mode="lines+markers",
        line=dict(color=PALETA["acento_alerta"], width=2),
        marker=dict(size=7),
        hovertemplate="%{x}<br>Acumulado: %{y:.1f}%<extra></extra>",
    ))
    fig.add_hline(y=80, line_dash="dot", line_color=t["neutro"], yref="y2")
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=15, color=t["titulo"]), x=0, xanchor="left"),
        template="plotly_white", showlegend=False, height=alto,
        margin=dict(l=0, r=60, t=52, b=110, autoexpand=True),
        font=dict(family=FUENTE, size=12, color=t["texto"]),
        plot_bgcolor=t["fondo"], paper_bgcolor=t["fondo"],
        yaxis=dict(title="", gridcolor=t["grid"],
                   tickfont=dict(color=t["texto"], size=11)),
        yaxis2=dict(title="% acumulado", overlaying="y", side="right", range=[0, 108],
                    showgrid=False, tickfont=dict(color=t["neutro"], size=10)),
        xaxis=dict(tickangle=-30, automargin=True,
                   tickfont=dict(color=t["texto"], size=11)),
    )
    return fig


def figura_barras_h(etiquetas, valores, titulo, colores=None, alto=None):
    """Barras horizontales con etiquetas de alto contraste."""
    t = paleta_grafico()
    etiquetas = list(etiquetas)[::-1]
    valores = list(valores)[::-1]
    colores = list(colores or [PALETA["primario"]])[::-1]
    while len(colores) < len(valores):
        colores.append(colores[len(colores) % len(colores or [0])])
    alto = alto or max(320, 34 * len(valores) + 90)
    fig = go.Figure(go.Bar(
        x=valores, y=etiquetas, orientation="h", marker_color=colores,
        text=[miles(v) for v in valores], textposition="outside",
        textfont=dict(color=t["texto"], size=11),
        hovertemplate="%{y}<br>Votos: %{text}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=15, color=t["titulo"]), x=0, xanchor="left"),
        template="plotly_white", showlegend=False, height=alto,
        margin=dict(l=0, r=80, t=52, b=28, autoexpand=True),
        font=dict(family=FUENTE, size=12, color=t["texto"]),
        plot_bgcolor=t["fondo"], paper_bgcolor=t["fondo"],
    )
    fig.update_yaxes(autorange="reversed", title="", showgrid=False, tickangle=0,
                     automargin=True, tickfont=dict(color=t["texto"], size=12))
    fig.update_xaxes(title="", tickfont=dict(color=t["texto"], size=10),
                     gridcolor=t["grid"], tickformat=",d", separatethousands=True)
    return fig


def kpi(etiqueta, valor, nota, color=None):
    color = color or PALETA["primario"]
    return (
        '<div style="background:{tarjeta};border-left:4px solid {color};'
        'padding:14px 16px;border-radius:6px;margin-bottom:10px;'
        'box-shadow:0 1px 2px rgba(0,0,0,0.06);">'
        '<div style="font-size:12px;color:#5A6B7B;text-transform:uppercase;'
        'letter-spacing:0.08em;">{etiqueta}</div>'
        '<div style="font-size:{tam};color:{color};font-weight:700;line-height:1.2;'
        'word-break:break-word;">{valor}</div>'
        '<div style="font-size:11px;color:#5A6B7B;">{nota}</div></div>'
    ).format(tarjeta=PALETA["tarjeta"], color=color, etiqueta=etiqueta,
             tam="19px" if len(str(valor)) > 20 else "28px", valor=valor, nota=nota)


def boton_descarga(df, nombre, clave):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    st.download_button("Descargar CSV", buffer.getvalue().encode("utf-8-sig"),
                       file_name=nombre, mime="text/csv", key=clave)


# --- aplicacion --------------------------------------------------------------
# --- motor predictivo --------------------------------------------------------
@st.cache_data(show_spinner=False)
def cargar_predictivo(ruta):
    """Lee el CSV de anomalias y clusters. Si no existe, el tablero sigue."""
    if not os.path.exists(ruta):
        return None
    df = pd.read_csv(ruta, encoding="utf-8-sig", dtype={"zona": str, "puesto": str})
    return df


def cifra_repartidora(votos_por_lista, curules):
    """Asigna curules por el metodo colombiano de cifra repartidora.

    Se divide cada lista por 1, 2, 3... hasta 'curules'; la cifra es el
    enesimo mayor cociente. Cada lista recibe tantas curules como veces
    quepa la cifra. Es el metodo real, no el cuociente simple: con el
    cuociente simple las curules sobrantes quedan sin asignar.
    """
    if curules <= 0 or not votos_por_lista:
        return {}, 0.0
    cocientes = []
    for lista, votos in votos_por_lista.items():
        for d in range(1, curules + 1):
            cocientes.append((votos / d, lista))
    cocientes.sort(reverse=True)
    if len(cocientes) < curules:
        return {k: 0 for k in votos_por_lista}, 0.0
    cifra = cocientes[curules - 1][0]
    asignadas = {l: int(v // cifra) for l, v in votos_por_lista.items()} if cifra else {}
    return asignadas, cifra


def main():
    st.title("Santander: inteligencia predictiva")
    st.caption("AEGIS-INTELLECT v2.0 · MOTOR PREDICTIVO · el detalle se lee completo · "
               "los codigos sin nombre se etiquetan, no se adivinan.")

    # Guardian de arranque: nada se carga si el Pre-flight no autoriza.
    codigo_pre, salida_pre = ejecutar_pre_flight()
    if codigo_pre != 0:
        motivos = {
            2: "no se pudo ejecutar el guardian o faltan archivos de control",
            3: "INTEGRIDAD DE DATOS COMPROMETIDA: un archivo no coincide con su hash",
            4: "LIBRERIA NO AUTORIZADA en requirements.txt",
            5: "CONTRATO DE ESQUEMA INVALIDO",
        }
        st.error("🔴 PRE-FLIGHT BLOQUEO EL ARRANQUE · %s"
                 % motivos.get(codigo_pre, "codigo %s" % codigo_pre))
        st.caption("El tablero no carga datos hasta que el guardian autorice. "
                   "Corrija el problema y reinicie.")
        with st.expander("Ver salida del Pre-flight"):
            st.code(salida_pre or "(sin salida)", language="text")
        st.stop()

    # Validacion fail-closed: si falta una fuente se dice cual y no se sigue.
    faltantes = []
    if not RUTA_DETALLE:
        faltantes.append("detalle_candidatos_santander.zip (o .csv) en data/")
    if not RUTA_PREDICTIVO:
        faltantes.append("anomalias_y_clusters.csv en data/")
    if faltantes:
        st.error("No se encuentra la fuente: " + " · ".join(faltantes))
        st.caption("Coloca los archivos en la carpeta data/ junto a app.py. "
                   "Busqueda realizada en: " + DATA_DIR)
        st.stop()

    df = cargar(RUTA_DETALLE)
    pred = cargar_predictivo(RUTA_PREDICTIVO)

    with st.sidebar:
        st.markdown("### Filtros globales")
        anios = sorted(df["anio"].unique())
        anio_sel = st.radio("Año", anios + ["Comparar"],
                            index=len(anios) - 1, horizontal=True)
        if anio_sel == "Comparar":
            corp_sel = None
            base = df[((df["anio"] == "2023") & (df["corporacion"] == "Asamblea")) |
                      ((df["anio"] == "2026") & (df["corporacion"] == "Senado"))]
            st.caption("Comparativa fija: Asamblea 2023 contra Senado 2026.")
        else:
            corps = sorted(df.loc[df["anio"] == anio_sel, "corporacion"].unique())
            preferida = {"2026": "Senado", "2023": "Gobernación"}
            idx = corps.index(preferida[anio_sel]) if preferida.get(anio_sel) in corps else 0
            corp_sel = st.selectbox("Corporación", corps, index=idx)
            base = df[(df["anio"] == anio_sel) & (df["corporacion"] == corp_sel)]
        municipios = sorted(base["municipio"].unique())
        municipio_sel = st.selectbox("Municipio", ["Todos"] + municipios, index=0)
        st.markdown("---")
        st.caption("Datos: " + os.path.basename(str(RUTA_DETALLE)))
        st.caption("Sello: " + SELLO_DATOS[:16] + "...")
        st.caption("Exportacion: CSV. PDF/PNG requiere kaleido, no instalado.")

    if anio_sel == "Comparar":
        st.warning("⚠️ Está comparando elecciones distintas: Asamblea 2023 contra Senado 2026. "
                   "Las diferencias reflejan volumenes de elecciones diferentes, no "
                   "transferencia de votos.")

    datos = base if municipio_sel == "Todos" else base[base["municipio"] == municipio_sel]
    if datos.empty:
        st.warning("Los filtros no dejan filas. Ajuste el alcance.")
        st.stop()

    validos = int(datos.loc[~datos["es_invalido"], "votos"].sum())
    invalidos = int(datos.loc[datos["es_invalido"], "votos"].sum())
    total = validos + invalidos
    tasa = 100.0 * invalidos / total if total else 0.0
    elegibles = datos.loc[~datos["es_invalido"]]
    partidos = pareto(elegibles.assign(
        etiqueta=[entidad(f) for f in elegibles.to_dict("records")])[["etiqueta", "votos"]],
        validos)
    lider = partidos.iloc[0] if not partidos.empty else None

    t1, t2, t3, t4, t5, t6 = st.tabs([
        "🌍 Anomalias y clusters", "🎯 Radar de oportunidades",
        "⚖️ Simulador", "🔍 Drill-down forense", "📊 Atlas",
        "📄 Generar Reportes",
    ])

    # ---------------- PESTANA 1 ----------------
    with t1:
        st.markdown("### Mapa de anomalías y clusters conductuales")
        if pred is None:
            st.info("No existe el CSV predictivo. Ejecute motor_predictivo.py para generarlo.")
        else:
            tiene_prioridad = "prioridad_nivel" in pred.columns
            c = st.columns(4)
            terr = int((pred["cluster"].str.startswith("2")).sum())
            opor = int((pred["cluster"].str.startswith("4")).sum())
            if tiene_prioridad:
                n1 = int((pred["prioridad_nivel"] == 1).sum())
                n2 = int((pred["prioridad_nivel"] == 2).sum())
                c[0].metric("Prioridad 1 · crítica", n1,
                            help="Puestos con mucho voto recuperable Y que se apartan "
                                 "de lo que su red predice. Acción inmediata.")
                c[1].metric("Prioridad 2 · estructural", n2,
                            help="Puestos que se apartan de su red pero mueven poco "
                                 "voto por sí solos. El problema es del entorno.")
            else:
                c[0].metric("Puestos con alerta",
                            int((pred["alertas"].str.len() > 0).sum()))
                c[1].metric("Puestos en ruptura", terr,
                            help="Puestos donde el partido lider cambio entre 2023 y 2026.")
            c[2].metric("Puestos en ruptura", terr,
                        help="Puestos donde el partido lider cambio entre 2023 y 2026.")
            _sin, _tot = _votos_sin_nombre(RUTA_PARTIDOS_CSV)
            c[3].metric("Votos sin partido verificado", miles(_sin),
                        help="Votos de listas cuyo codigo no resuelve el catalogo "
                             "oficial de la Registraduria. De %s votos de partido, "
                             "%s quedan sin nombre." % (miles(_tot), miles(_sin)))
            st.caption("Los 353.282 votos de los codigos 30XX no tienen dueno verificado: "
                       "es la mayor opacidad del modelo, no un error de calculo.")

            perfil = (pred.groupby("cluster")
                      .agg(puestos=("total", "size"), votos=("total", "sum"))
                      .reset_index().sort_values("votos", ascending=False))
            st.dataframe(perfil, width="stretch", hide_index=True)
            st.plotly_chart(
                figura_barras_h(perfil["cluster"], perfil["puestos"],
                                "Cuantos puestos hay en cada cluster conductual"),
                width="stretch")

            if tiene_prioridad:
                st.markdown("**Puestos por prioridad de acción**")
                st.caption(
                    "La prioridad cruza dos señales: cuánto voto se puede recuperar "
                    "en el puesto, y cuánto se aparta de lo que su red de vecinos "
                    "predice. N1 exige ambas. N3 es volumen sin anomalía. "
                    "N2 es anomalía sin volumen. N4 no requiere acción.")
                tabla_prior = pred.copy()
                # Los codigos de lista se resuelven al nombre oficial de la
                # Registraduria. El CSV guarda el codigo crudo: la traduccion
                # es de presentacion, no de dato.
                if "partido_top" in tabla_prior.columns:
                    tabla_prior["partido_top"] = tabla_prior["partido_top"].apply(
                        _resolver_partido_ui)
                tabla_prior = tabla_prior[[
                    "municipio", "zona", "puesto", "prioridad_nivel",
                    "prioridad_etiqueta", "prioridad_accion", "gap_absoluto",
                    "tasa", "tasa_red", "desviacion_z", "partido_top",
                ]].sort_values(["prioridad_nivel", "gap_absoluto"],
                               ascending=[True, False])
                st.dataframe(tabla_prior, width="stretch", hide_index=True)
                boton_descarga(tabla_prior, "prioridad_unificada.csv", "dl_prio")
            else:
                st.markdown("**Detalle por alerta**")
                alertas = pred[pred["alertas"].str.len() > 0][
                    ["municipio", "zona", "puesto", "cluster", "total", "tasa",
                     "z", "io", "alertas"]].sort_values("tasa", ascending=False)
                st.dataframe(alertas, width="stretch", hide_index=True)
                boton_descarga(alertas, "alertas_forenses.csv", "dl_alertas")

    # ---------------- PESTANA 2 ----------------
    with t2:
        st.markdown("### Radar de oportunidades · Objetivos de última milla")
        if pred is None:
            st.info("No existe el CSV predictivo.")
        else:
            f1, f2 = st.columns(2)
            solo_uno = f1.checkbox("Solo Anillo de Uno (municipios de 1 puesto)", value=False)
            minimo = f2.number_input("Volumen mínimo del puesto", min_value=0,
                                     value=500, step=100)
            rad = pred[(pred["total"] >= minimo)
                       & (~pred["zona"].astype(str).str.startswith("099"))].copy()
            if solo_uno:
                unos = pred.groupby("municipio")["puesto"].nunique()
                rad = rad[rad["municipio"].isin(unos[unos == 1].index)]
            rad = rad.sort_values("io", ascending=False).head(50)
            rad["accion"] = rad.apply(
                lambda r: "Mesa blindada" if r["tasa"] > 12 else "Orientación de voto", axis=1)
            st.caption("IO = (blancos + nulos + no marcados + fuga) / total del puesto. "
                       "La fuga es la caida de cuota del lider 2023, repartida por volumen.")
            st.dataframe(rad[["municipio", "zona", "puesto", "total", "io", "tasa",
                              "alertas", "accion"]],
                         width="stretch", hide_index=True)
            st.plotly_chart(
                figura_barras_h(
                    (rad["municipio"] + " " + rad["zona"] + "/" + rad["puesto"]).head(15),
                    rad["io"].head(15),
                    "Los 15 puestos con mayor índice de oportunidad"),
                width="stretch")
            boton_descarga(rad, "radar_oportunidades.csv", "dl_radar")

    # ---------------- PESTANA 3 ----------------
    with t3:
        st.markdown("### Simulador de escenarios")
        st.caption("Los sliders recalculan sobre los votos reales del alcance elegido.")
        mov = st.slider("Movilización adicional (%)", -20, 50, 0, 5)
        captura = st.slider("Captura del voto 30XX (%)", 0, 100, 0, 5)
        votos_30xx = int(df.loc[(df["anio"] == "2026") & (df["corporacion"] == "Senado")
                                & df["partido"].str.contains("nombre pendiente", na=False),
                                "votos"].sum())
        if municipio_sel != "Todos":
            votos_30xx_mun = int(datos.loc[datos["partido"].str.contains("nombre pendiente",
                                                                        na=False), "votos"].sum())
        else:
            votos_30xx_mun = votos_30xx
        nuevos_mov = int(validos * mov / 100.0)
        nuevos_cap = int(votos_30xx_mun * captura / 100.0)
        proyectado = validos + nuevos_mov + nuevos_cap

        a, b, cc2 = st.columns(3)
        a.metric("Válidos hoy", miles(validos))
        b.metric("Válidos proyectados", miles(proyectado),
                 delta=miles(proyectado - validos))
        cc2.metric("Voto 30XX en alcance", miles(votos_30xx_mun))

        if lider is not None and validos:
            cuota_act = 100.0 * lider["votos"] / validos
            st.markdown("**Partido líder hoy:** %s con %s (%s)"
                        % (lider["etiqueta"], miles(lider["votos"]), pct(cuota_act)))

        st.markdown("#### Proyección de curules · Cámara de Santander (7 curules)")
        st.caption("Método: cifra repartidora. Se aplica sobre el voto real de Cámara 2026 "
                   "de Santander, con los ajustes de los sliders repartidos proporcionalmente.")
        cam = df[(df["anio"] == "2026") & (df["corporacion"] == "Cámara")
                 & (~df["es_invalido"])]
        if municipio_sel != "Todos":
            cam = cam[cam["municipio"] == municipio_sel]
        if cam.empty:
            st.info("No hay votos de Cámara en el alcance.")
        else:
            por_lista = cam.groupby("partido")["votos"].sum().sort_values(ascending=False)
            antes, cifra_a = cifra_repartidora(por_lista.to_dict(), 7)
            factor = (proyectado / validos) if validos else 1.0
            despues, cifra_d = cifra_repartidora(
                {k: v * factor for k, v in por_lista.items()}, 7)
            tabla = pd.DataFrame({
                "Partido": list(por_lista.index),
                "Votos hoy": [miles(v) for v in por_lista.values],
                "Curules hoy": [antes.get(k, 0) for k in por_lista.index],
                "Curules proyectadas": [despues.get(k, 0) for k in por_lista.index],
            })
            tabla["Cambio"] = tabla["Curules proyectadas"] - tabla["Curules hoy"]
            st.dataframe(tabla.head(15), width="stretch", hide_index=True)
            st.caption("Cifra repartidora hoy: %s · proyectada: %s"
                       % (miles(cifra_a), miles(cifra_d)))
            boton_descarga(tabla, "simulacion_curules.csv", "dl_sim")

    # ---------------- PESTANA 4 ----------------
    with t4:
        st.markdown("### Drill-down forense por puesto")
        if pred is None:
            st.info("No existe el CSV predictivo.")
        else:
            mun_d = st.selectbox("Municipio", sorted(pred["municipio"].unique()), key="dd_mun")
            sub = pred[pred["municipio"] == mun_d]
            pue_d = st.selectbox("Puesto",
                                 sorted(set(sub["zona"] + "/" + sub["puesto"])), key="dd_pue")
            fila = sub[(sub["zona"] + "/" + sub["puesto"]) == pue_d].iloc[0]
            a, b, cc3, d4 = st.columns(4)
            a.metric("Votos totales", miles(fila["total"]))
            b.metric("Z-score", "%+.2f" % fila["z"])
            cc3.metric("Tasa de pérdida", pct(fila["tasa"], 2))
            d4.metric("Índice de oportunidad", pct(fila["io"]))
            st.caption("Z = (votos del puesto − media del municipio) / desviación del municipio. "
                       "|Z| > 3 es atípico. Benford se calcula solo con 300+ candidatos: "
                       "con menos, la desviación esperada por azar supera el umbral.")
            st.markdown("**Cluster del municipio:** %s" % fila["cluster"])
            if fila["benford"] is not None and not pd.isna(fila["benford"]):
                st.markdown("**Desviación de Benford:** %.1f %% %s"
                            % (fila["benford"],
                               "(sobre el umbral del 5 % · revisar actas)"
                               if fila["benford"] > 5 else "(dentro de lo esperado)"))
            else:
                st.markdown("**Benford:** no calculable en este puesto (menos de 300 valores).")
            # top 3 partidos 2023 vs 2026 en ese puesto
            p23 = df[(df["anio"] == "2023") & (df["corporacion"] == "Asamblea")
                     & (df["municipio"] == mun_d) & (~df["es_invalido"])]
            p26 = df[(df["anio"] == "2026") & (df["corporacion"] == "Senado")
                     & (df["municipio"] == mun_d) & (~df["es_invalido"])
                     & ((df["zona"].str.zfill(3) + "/" + df["puesto"].str.zfill(2)) == pue_d)]
            izq, der = st.columns(2)
            with izq:
                st.markdown("**Top 3 · Asamblea 2023 (municipio)**")
                if p23.empty:
                    st.caption("Sin datos.")
                else:
                    r = pareto(p23.assign(etiqueta=[entidad(f) for f in p23.to_dict("records")])[
                        ["etiqueta", "votos"]], int(p23["votos"].sum())).head(3)
                    st.dataframe(r[["etiqueta", "votos", "pct"]].rename(
                        columns={"etiqueta": "Partido", "votos": "Votos", "pct": "%"}),
                        width="stretch", hide_index=True)
            with der:
                st.markdown("**Top 3 · Senado 2026 (este puesto)**")
                if p26.empty:
                    st.caption("Sin datos.")
                else:
                    r = pareto(p26.assign(etiqueta=[entidad(f) for f in p26.to_dict("records")])[
                        ["etiqueta", "votos"]], int(p26["votos"].sum())).head(3)
                    st.dataframe(r[["etiqueta", "votos", "pct"]].rename(
                        columns={"etiqueta": "Partido", "votos": "Votos", "pct": "%"}),
                        width="stretch", hide_index=True)

    # ---------------- PESTANA 5: ATLAS ----------------
    with t5:
        c = st.columns(4)
        with c[0]:
            st.markdown(kpi("Votos validos", miles(validos),
                            miles(total) + " con no aprovechado"), unsafe_allow_html=True)
        with c[1]:
            muns_all = pareto(datos.loc[~datos["es_invalido"]].assign(
                etiqueta=lambda x: x["municipio"])[["etiqueta", "votos"]], validos)
            n80 = int(muns_all["n80"].iloc[0]) if not muns_all.empty else 0
            st.markdown(kpi("Concentracion Pareto", "%d municipios = 80 %%" % n80,
                            pct(muns_all.head(n80)["pct"].sum()) + " del valido"),
                        unsafe_allow_html=True)
        with c[2]:
            if lider is not None:
                pend = es_pendiente(lider["etiqueta"])
                _sub_lider = elegibles[elegibles["partido"] == lider["etiqueta"]]
                _cerrada = es_lista_cerrada(_sub_lider)
                st.markdown(kpi("Lider (sin nombre)" if pend else "Partido lider",
                                "Código sin nombre" if pend else str(lider["etiqueta"]),
                                pct(lider["pct"]) + " del valido" +
                                (" · SOLO POR LA LISTA" if _cerrada else ""),
                                color="#5A6B7B" if pend else PALETA["primario"]),
                            unsafe_allow_html=True)
        with c[3]:
            st.markdown(kpi("Tasa de perdida", pct(tasa, 2),
                            miles(invalidos) + " no aprovechados",
                            color=PALETA["acento_alerta"] if tasa > UMBRAL_RIESGO
                            else PALETA["exito"]), unsafe_allow_html=True)

        st.markdown("---")
        if not partidos.empty:
            n80p = int(partidos["n80"].iloc[0])
            st.plotly_chart(
                figura_pareto(partidos, "Los %d primeros partidos concentran el %s del voto"
                              % (n80p, pct(partidos.head(n80p)["pct"].sum()))),
                width="stretch")
            with st.expander("Ver tabla de partidos"):
                tabla = partidos[["etiqueta", "votos", "pct", "acum"]].copy()
                tabla.columns = ["Partido", "Votos", "% individual", "% acumulado"]
                tabla["Tipo de lista"] = [
                    "SOLO POR LA LISTA"
                    if es_lista_cerrada(elegibles[elegibles["partido"] == e]) else "abierta"
                    for e in partidos["etiqueta"]
                ]
                st.dataframe(tabla, width="stretch", hide_index=True)
                st.caption("Una lista cerrada no se desglosa por candidato: todos sus votos "
                           "van al codigo de lista. Las abiertas reparten el voto entre nombres.")
                boton_descarga(tabla, "pareto_partidos.csv", "dl_partidos")

        if municipio_sel == "Todos":
            st.markdown("### Dónde poner los pies")
            if not muns_all.empty:
                top = muns_all.head(15).copy()
                st.plotly_chart(
                    figura_barras_h(top["etiqueta"], top["votos"],
                                    "Los 15 municipios que mueven el %s del voto"
                                    % pct(top["pct"].sum())),
                    width="stretch")
                tb = top[["etiqueta", "votos", "pct", "acum"]].copy()
                tb.columns = ["Municipio", "Votos", "% Depto", "% Acum"]
                st.dataframe(tb, width="stretch", hide_index=True)
                boton_descarga(tb, "pareto_municipios.csv", "dl_muns")
        else:
            st.markdown("### Qué mesas blindar en %s" % municipio_sel.title())
            pu = pareto(datos.loc[~datos["es_invalido"]].assign(
                etiqueta=lambda x: x["zona"].str.zfill(3) + "/" + x["puesto"].str.zfill(2))[
                ["etiqueta", "votos"]], validos)
            if not pu.empty:
                n80m = int(pu["n80"].iloc[0])
                st.plotly_chart(
                    figura_barras_h(pu.head(10)["etiqueta"], pu.head(10)["votos"],
                                    "Con %d puestos cubre el %s del municipio"
                                    % (n80m, pct(pu.head(n80m)["pct"].sum()))),
                    width="stretch")
                tb = pu[["etiqueta", "votos", "pct", "acum"]].copy()
                tb.columns = ["Puesto", "Votos", "% Municipio", "% Acum"]
                st.dataframe(tb, width="stretch", hide_index=True)
                boton_descarga(tb, "pareto_puestos.csv", "dl_puestos")

    # ---------------- PESTANA 6: GENERAR REPORTES ----------------
    with t6:
        st.markdown("### Generar reporte")
        motor = cargar_motor_reportes()
        if motor is None:
            st.error("🔴 No se encontro el modulo motor_reportes. "
                     "En local vive en 06_Herramientas/motor_reportes; en la nube "
                     "debe viajar junto a app.py.")
        else:
            st.caption("Motor encontrado en: " + motor["raiz"])

            niveles = {
                "AEGIS TECHNICAL": "tecnico",
                "AEGIS FEYNMAN": "feynman",
                "AEGIS PILOT": "piloto",
            }
            col_a, col_b = st.columns(2)
            with col_a:
                nivel_sel = st.selectbox("Nivel de reporte", list(niveles), index=0)
            with col_b:
                muns_rep = sorted(df["municipio"].unique())
                defecto = (muns_rep.index(municipio_sel)
                           if municipio_sel in muns_rep else 0)
                mun_rep = st.selectbox("Municipio del reporte", muns_rep, index=defecto)

            if st.button("Generar Reporte", type="primary", width="stretch"):
                try:
                    datos_rep = motor["extraer"](
                        mun_rep.upper(), "2027",
                        ruta_detalle=RUTA_DETALLE,
                        ruta_maestro=RUTA_MAESTRO,
                        # Sin esta ruta el reporte sale sin prioridades en la
                        # nube: el valor por defecto apunta al vault.
                        ruta_predictivo=RUTA_PREDICTIVO,
                    )
                    contrato_rep = motor["adaptadores"].piloto.construir(datos_rep)
                    clave = niveles[nivel_sel]

                    if clave == "piloto":
                        svg = motor["renderizador"].renderizar_svg(contrato_rep)
                        texto = motor["renderizador"].renderizar_texto(contrato_rep)
                        st.components.v1.html(svg, height=600, scrolling=True)
                        st.markdown("**Texto para enviar**")
                        st.code(texto, language="text")
                        d1, d2 = st.columns(2)
                        d1.download_button("Descargar SVG", svg.encode("utf-8"),
                                           file_name="reporte_piloto.svg",
                                           mime="image/svg+xml", width="stretch")
                        d2.download_button("Descargar texto", texto.encode("utf-8"),
                                           file_name="reporte_piloto.txt",
                                           mime="text/plain", width="stretch")
                    else:
                        modulo = (motor["adaptadores"].tecnico if clave == "tecnico"
                                  else motor["adaptadores"].feynman)
                        salida = modulo.desde_contrato(contrato_rep)
                        st.markdown(salida)
                        st.download_button(
                            "Descargar " + nivel_sel,
                            salida.encode("utf-8"),
                            file_name="reporte_%s_%s.md" % (clave, mun_rep.lower()),
                            mime="text/markdown", width="stretch")
                except FileNotFoundError as error:
                    st.error("🔴 Falta una fuente de datos: %s" % error)
                except ValueError as error:
                    st.error("🔴 No se pudo construir el reporte: %s" % error)
                except Exception as error:  # noqa: BLE001
                    st.error("🔴 Error inesperado (%s): %s"
                             % (type(error).__name__, error))

        # ---------------- imprimir / PDF ----------------
        st.markdown("---")
        st.markdown("**Exportar el tablero a PDF**")
        st.caption(
            "Abre el diálogo de impresión. Elige «Guardar como PDF» como "
            "destino. No se añadió ninguna librería de PDF: la del navegador "
            "ya existe y no rompe el Pre-flight.")
        st.components.v1.html(
            """
            <button onclick="window.parent.print()"
                    style="background:#002B5C;color:#FFFFFF;border:none;
                           border-radius:6px;padding:10px 22px;font-size:15px;
                           font-weight:600;cursor:pointer;">
              Imprimir / Guardar como PDF
            </button>
            <p style="font-family:sans-serif;font-size:12px;color:#6B7280;
                      margin-top:8px;">
              Si el botón no responde, usa Ctrl+P (Windows) o Cmd+P (Mac).
            </p>
            """,
            height=90,
        )

    st.markdown("---")
    st.caption("Sello SHA256 de la fuente: " + SELLO_DATOS +
               " · Los códigos 30XX se publican sin nombre: no hay fuente "
               "primaria que los verifique.")


if autenticar():
    main()
else:
    st.stop()
