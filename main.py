import streamlit as st
import pandas as pd
import numpy as np
import requests
import base64
from datetime import date, datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
from io import StringIO
import re
import json
import uuid
from streamlit_option_menu import option_menu

st.set_page_config(page_title="Salud", layout="wide")

st.markdown("""
<style>
/* ── Fuente sistema ── */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                 "Helvetica Neue", Arial, sans-serif !important;
    color: #1C1C1E !important;
}

/* ── Fondo gris iOS en toda la app ── */
.stApp,
header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
footer,
.stSidebar,
[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {
    background-color: #F2F2F7 !important;
    color: #1C1C1E !important;
}

/* ── Contenido principal ── */
.main .block-container {
    background-color: #F2F2F7 !important;
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
}

/* ── Inputs, selects, text areas ── */
input, textarea,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTimeInput"] input,
[data-testid="stSelectbox"] > div,
[data-baseweb="input"], [data-baseweb="textarea"],
[data-baseweb="select"] > div,
[data-baseweb="base-input"] {
    background-color: #FFFFFF !important;
    color: #1C1C1E !important;
    border-color: #E5E5EA !important;
    border-radius: 10px !important;
}

/* ── Formularios ── */
[data-testid="stForm"] {
    background: #FFFFFF !important;
    border: none !important;
    border-radius: 13px !important;
    padding: 16px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07), 0 0 0 0.5px rgba(0,0,0,0.05) !important;
}

/* ── Tablas y DataEditor — solo forma exterior, sin tocar el canvas interno ── */
[data-testid="stDataFrame"] > div:first-child,
[data-testid="stDataEditor"] > div:first-child {
    border-radius: 13px !important;
    overflow: hidden !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07), 0 0 0 0.5px rgba(0,0,0,0.05) !important;
    border: none !important;
}

/* ── Tarjetas de métricas ── */
[data-testid="metric-container"] {
    background: #FFFFFF !important;
    border-radius: 13px !important;
    padding: 14px 16px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07), 0 0 0 0.5px rgba(0,0,0,0.05) !important;
}
[data-testid="stMetricValue"] {
    font-size: 26px !important; font-weight: 700 !important;
    color: #1C1C1E !important; letter-spacing: -0.5px !important;
}
[data-testid="stMetricLabel"] {
    font-size: 11px !important; font-weight: 500 !important;
    color: #8E8E93 !important; text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}
[data-testid="stMetricDelta"] { font-size: 13px !important; }

/* ── Títulos ── */
h1 {
    font-size: 28px !important; font-weight: 700 !important;
    color: #1C1C1E !important; letter-spacing: -0.3px !important;
    margin-bottom: 12px !important;
}
h2, h3 {
    font-size: 17px !important; font-weight: 600 !important;
    color: #1C1C1E !important; margin-top: 20px !important;
}
.stMarkdown p, .stText p, label { color: #1C1C1E !important; }

/* ── Botones ── */
.stButton > button {
    border-radius: 10px !important; font-weight: 600 !important;
    font-size: 15px !important; transition: opacity .15s !important;
    border: none !important;
}
.stButton > button:hover { opacity: 0.8 !important; }
.stButton > button[kind="primary"] {
    background: #007AFF !important; color: #fff !important;
}
.stButton > button[kind="secondary"] {
    background: #E5E5EA !important; color: #007AFF !important;
}

/* ── Expanders ── */
details {
    background: #FFFFFF !important; border-radius: 13px !important;
    border: none !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07), 0 0 0 0.5px rgba(0,0,0,0.05) !important;
    margin-bottom: 8px !important;
}
details summary {
    font-weight: 600 !important; font-size: 15px !important;
    color: #1C1C1E !important; padding: 12px 16px !important;
    background: #FFFFFF !important;
}

/* ── Alertas / info boxes ── */
.stAlert { border-radius: 12px !important; border: none !important; }

/* ── Captions ── */
.stCaption p { font-size: 12px !important; color: #8E8E93 !important; line-height: 1.45 !important; }

/* ── Dividers ── */
hr { border: none !important; border-top: 0.5px solid #C6C6C8 !important; margin: 14px 0 !important; }

/* ── Slider ── */
[data-testid="stSlider"] > div { background: transparent !important; }

/* ── Menú horizontal ── */
nav[class*="nav"] {
    background: #FFFFFF !important;
    border-radius: 13px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07), 0 0 0 0.5px rgba(0,0,0,0.05) !important;
    margin-bottom: 12px !important;
}

/* ── Móvil: menú compacto ── */
@media (max-width: 640px) {
    .nav-link span { font-size: 10px !important; display: block !important; margin-top: 2px !important; }
    .nav-link { padding: 6px 4px !important; }
    .nav-link i { font-size: 18px !important; display: block !important; }
    .main .block-container { padding-left: 0.75rem !important; padding-right: 0.75rem !important; }
}
</style>
""", unsafe_allow_html=True)

REPO = "teresamattil/registro_salud"
FILE = "comidas.csv"
API_URL = f"https://api.github.com/repos/{REPO}/contents/{FILE}"
TOKEN = st.secrets["GITHUB_TOKEN"]
GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
HEADERS = {"Authorization": f"token {TOKEN}"}
objetivo = 1500  # Calorías diarias objetivo

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-3-flash-preview")

MOMENTOS = [
    "Desayuno",
    "Entre horas (antes de comer)",
    "Comida",
    "Entre horas (antes de cenar)",
    "Cena",
]
HORAS_MOMENTO = {
    "Desayuno": "09:00",
    "Entre horas (antes de comer)": "11:30",
    "Comida": "14:30",
    "Entre horas (antes de cenar)": "18:00",
    "Cena": "21:30",
}

def _momento_desde_hora(hora):
    try:
        h, m = map(int, str(hora)[:5].split(":"))
        minutos = h * 60 + m
    except (ValueError, TypeError):
        return "Comida"
    if minutos < 10 * 60 + 30:
        return "Desayuno"
    if minutos < 13 * 60:
        return "Entre horas (antes de comer)"
    if minutos < 16 * 60 + 30:
        return "Comida"
    if minutos < 19 * 60 + 30:
        return "Entre horas (antes de cenar)"
    return "Cena"

@st.cache_data(ttl=60)
def load_data():
    r = requests.get(API_URL, headers=HEADERS).json()
    if "content" not in r:
        return pd.DataFrame(columns=["Fecha","momento","hora","comida","ruta_foto","calorías_estimadas",
                                      "carbohidratos_g","proteinas_g","sodio_nivel"])
    content = base64.b64decode(r["content"])
    d = pd.read_csv(pd.io.common.BytesIO(content))
    migrated = "momento" not in d.columns
    if "momento" not in d.columns:
        d["momento"] = d["hora"].apply(_momento_desde_hora) if "hora" in d.columns else "Comida"
    else:
        d["momento"] = d["momento"].fillna("").astype(str).str.strip()
        missing = d["momento"].eq("")
        if missing.any():
            d.loc[missing, "momento"] = d.loc[missing, "hora"].apply(_momento_desde_hora)
            migrated = True
    for col in ["carbohidratos_g", "proteinas_g", "sodio_nivel"]:
        if col not in d.columns:
            d[col] = pd.NA
            migrated = True
    if migrated:
        save_data(d, "Migrar comidas: añadir momento")
    return d

def save_data(df, message):
    r_api = requests.get(API_URL, headers=HEADERS).json()
    sha = r_api["sha"]
    content = base64.b64encode(df.to_csv(index=False).encode()).decode()
    requests.put(API_URL, headers=HEADERS, json={"message": message, "content": content, "sha": sha})

@st.cache_data(ttl=3600)
def load_peso():
    dp = pd.read_csv("data/peso_diario.csv")
    dp["Date"] = pd.to_datetime(dp["Date"]).dt.date
    dp = dp.groupby("Date", as_index=False)["Body mass(kg)"].mean()
    dp.columns = ["Fecha", "peso_kg"]
    return dp

@st.cache_data(ttl=3600)
def load_basal_energy():
    d = pd.read_csv("data/basal_energy.csv")
    d["Fecha"] = pd.to_datetime(d["Date"]).dt.date
    d["basal_kcal"] = d["Basal energy burned(kcal)"]
    return d[["Fecha", "basal_kcal"]]

@st.cache_data(ttl=3600)
def load_active_energy():
    d = pd.read_csv("data/active_energy.csv")
    d["Fecha"] = pd.to_datetime(d["Date"]).dt.date
    d["activo_kcal"] = pd.to_numeric(d["Active energy burned(kcal)"], errors="coerce")
    return d[["Fecha", "activo_kcal"]]

@st.cache_data(ttl=3600)
def load_sleep_data():
    d = pd.read_csv("data/sleep_time.csv")
    rows = []
    for _, row in d.iterrows():
        parts = str(row["Date"]).strip().split(" - ")
        if len(parts) != 2:
            continue
        try:
            end_dt = pd.to_datetime(parts[1])
            horas = float(row["Time in bed(hr)"])
        except Exception:
            continue
        if horas <= 1.0:
            continue
        rows.append({"Fecha": end_dt.date(), "horas_cama": horas})
    if not rows:
        return pd.DataFrame(columns=["Fecha", "horas_cama"])
    return pd.DataFrame(rows).groupby("Fecha", as_index=False)["horas_cama"].sum()

@st.cache_data(ttl=3600)
def load_ciclo():
    d = pd.read_csv("data/ciclo.csv")
    d["inicio"] = pd.to_datetime(d["Fecha_inicio_cliclo"], dayfirst=True).dt.date
    d["fin"] = pd.to_datetime(d["Fecha_fin_ciclo"], dayfirst=True).dt.date
    d["dias_regla"] = pd.to_numeric(d["dias_periodo"], errors="coerce").fillna(5).astype(int)
    return d[["inicio", "fin", "dias_regla"]].dropna(subset=["inicio", "fin"])

def _fase(fecha, ciclos):
    for _, c in ciclos.iterrows():
        if c["inicio"] <= fecha <= c["fin"]:
            dia = (fecha - c["inicio"]).days + 1
            dur = (c["fin"] - c["inicio"]).days + 1
            if dia <= c["dias_regla"]:
                return dia, 1, 0   # dia_ciclo, es_menstrual, es_lutea
            elif dia >= dur - 13:
                return dia, 0, 1
            else:
                return dia, 0, 0
    return np.nan, 0, 0

RUTINAS_FILE = "rutinas.json"
RUTINAS_API_URL = f"https://api.github.com/repos/{REPO}/contents/{RUTINAS_FILE}"


def load_routines():
    try:
        response = requests.get(RUTINAS_API_URL, headers=HEADERS, timeout=20)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        content = base64.b64decode(response.json()["content"])
        data = json.loads(content.decode("utf-8"))
        return data if isinstance(data, list) else []
    except Exception as exc:
        st.warning(f"No se pudieron cargar las rutinas: {exc}")
        return []


def save_routines(routines):
    response = requests.get(RUTINAS_API_URL, headers=HEADERS, timeout=20)
    payload = {
        "message": "Actualizar rutinas de comidas",
        "content": base64.b64encode(json.dumps(routines, ensure_ascii=False, indent=2).encode("utf-8")).decode("utf-8"),
    }
    if response.status_code == 200:
        payload["sha"] = response.json()["sha"]
    elif response.status_code != 404:
        response.raise_for_status()
    result = requests.put(RUTINAS_API_URL, headers=HEADERS, json=payload, timeout=20)
    result.raise_for_status()


def _normalizar_rutinas(data):
    """Migra rutinas antiguas de un solo alimento al nuevo formato calendario."""
    normalizadas = []
    for i, rutina in enumerate(data or []):
        if not isinstance(rutina, dict):
            continue
        nombre = str(rutina.get("nombre", f"Rutina {i+1}")).strip() or f"Rutina {i+1}"
        rid = str(rutina.get("id") or uuid.uuid5(uuid.NAMESPACE_URL, f"registro_salud:{nombre}").hex)
        momento = rutina.get("momento", "Comida")
        if momento not in MOMENTOS:
            momento = "Comida"
        dias = rutina.get("dias_semana", list(range(7)))
        try:
            dias = sorted({int(d) for d in dias if 0 <= int(d) <= 6})
        except (TypeError, ValueError):
            dias = list(range(7))
        items = rutina.get("items")
        if not isinstance(items, list):
            # Compatibilidad con las rutinas antiguas (un alimento por rutina).
            items = [{
                "descripcion": rutina.get("comida", nombre),
                "kcal": rutina.get("kcal", 0),
                "carbohidratos_g": rutina.get("carbohidratos_g"),
                "proteinas_g": rutina.get("proteinas_g"),
                "sodio_nivel": rutina.get("sodio_nivel"),
            }]
        items_limpios = []
        for item in items:
            if not isinstance(item, dict) or not str(item.get("descripcion", "")).strip():
                continue
            try:
                kcal = float(item.get("kcal", 0) or 0)
            except (TypeError, ValueError):
                kcal = 0.0
            items_limpios.append({
                "descripcion": str(item.get("descripcion", "")).strip(),
                "kcal": kcal,
                "carbohidratos_g": item.get("carbohidratos_g"),
                "proteinas_g": item.get("proteinas_g"),
                "sodio_nivel": item.get("sodio_nivel"),
            })
        normalizadas.append({"id": rid, "nombre": nombre, "momento": momento,
                             "dias_semana": dias, "items": items_limpios})
    return normalizadas


def _rutina_aplica(rutina, fecha):
    return fecha.weekday() in rutina.get("dias_semana", list(range(7)))


def _registrar_rutina(df_actual, rutina, fecha):
    nuevas = []
    for item in rutina.get("items", []):
        fila = _empty_food_row(fecha, rutina["momento"], item["descripcion"], item.get("kcal", 0),
                               item.get("carbohidratos_g"), item.get("proteinas_g"), item.get("sodio_nivel"))
        fila["rutina_id"] = rutina["id"]
        nuevas.append(fila)
    if nuevas:
        return pd.concat([df_actual, pd.DataFrame(nuevas)], ignore_index=True)
    return df_actual


def _empty_food_row(fecha, momento, descripcion, kcal=0, carbs=None, proteinas=None, sodio=None):
    return {
        "Fecha": fecha,
        "momento": momento,
        "hora": HORAS_MOMENTO.get(momento, "14:30"),
        "comida": descripcion,
        "ruta_foto": "",
        "calorías_estimadas": kcal,
        "carbohidratos_g": carbs,
        "proteinas_g": proteinas,
        "sodio_nivel": sodio,
        "rutina_id": "",
    }


def _parse_week_with_gemini(texto, lunes):
    prompt = f"""Eres un asistente de registro nutricional. Convierte el texto de una semana de comidas en registros individuales.
La semana comienza el lunes {lunes.isoformat()} y termina el domingo siguiente.
Interpreta referencias como "el lunes", "ayer", "todos los días" o "de lunes a viernes" respecto a esa semana.
Si una comida o hábito se indica como diario/todos los días, crea una fila independiente para cada día aplicable.
No inventes comidas que no aparezcan. Estima calorías, carbohidratos y proteínas para la ración descrita. Sodio debe ser "bajo", "medio" o "alto".
Usa exclusivamente estos momentos: {json.dumps(MOMENTOS, ensure_ascii=False)}.
Si el momento no está claro, dedúcelo por el tipo de comida y contexto; no inventes horas.
Devuelve ÚNICAMENTE un array JSON. Cada objeto debe tener exactamente estas claves:
fecha (YYYY-MM-DD), momento, descripcion, calorias (número), carbohidratos_g (número), proteinas_g (número), sodio_nivel (bajo/medio/alto).
TEXTO DEL USUARIO:
{texto}"""
    response = model.generate_content(prompt)
    raw = response.text.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Gemini no ha devuelto una lista de comidas.")
    rows = []
    for item in data:
        fecha = pd.to_datetime(item["fecha"]).date()
        momento = item.get("momento", "Comida")
        if momento not in MOMENTOS:
            momento = "Comida"
        rows.append({
            "Fecha": fecha,
            "momento": momento,
            "hora": HORAS_MOMENTO[momento],
            "comida": str(item.get("descripcion", "")).strip(),
            "ruta_foto": "",
            "calorías_estimadas": pd.to_numeric(item.get("calorias", 0), errors="coerce"),
            "carbohidratos_g": pd.to_numeric(item.get("carbohidratos_g"), errors="coerce"),
            "proteinas_g": pd.to_numeric(item.get("proteinas_g"), errors="coerce"),
            "sodio_nivel": item.get("sodio_nivel", "medio"),
        })
    return pd.DataFrame(rows)


df = load_data()
for col, default in [("momento", "Comida"), ("ruta_foto", ""), ("calorías_estimadas", 0),
                     ("carbohidratos_g", pd.NA), ("proteinas_g", pd.NA), ("sodio_nivel", pd.NA),
                     ("rutina_id", "")]:
    if col not in df.columns:
        df[col] = default
df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
df["calorías_estimadas"] = pd.to_numeric(df["calorías_estimadas"], errors="coerce").fillna(0)
df["momento"] = df["momento"].fillna("Comida")
rutinas = _normalizar_rutinas(load_routines())

# Persistir automáticamente la migración de las rutinas antiguas al formato calendario.
if rutinas and any("items" not in r for r in load_routines() if isinstance(r, dict)):
    save_routines(rutinas)

def _run_estimacion(df_global, save=True):
    """Llama a Gemini para estimar calorías y macros de las filas pendientes."""
    pendientes = df_global[df_global["calorías_estimadas"] == 0.0].copy()
    if pendientes.empty:
        return df_global, 0
    csv_text = pendientes.rename(columns={
        "Fecha":"fecha","hora":"hora","comida":"descripcion","calorías_estimadas":"calorias"
    })[["fecha","hora","descripcion","calorias"]].to_csv(index=False)
    prompt = f"""ROL: Eres un asistente nutricional especializado en estimación de alimentos consumidos en España.
OBJETIVO: Para los ítems con calorias=0.0, estima simultáneamente calorías y macronutrientes.
CAMPOS A ESTIMAR (solo donde calorias=0.0):
- calorias: kilocalorías totales de la porción
- carbohidratos_g: carbohidratos totales en gramos
- proteinas_g: proteínas en gramos
- sodio_nivel: "bajo" / "medio" / "alto"
  * bajo: <300mg sodio (frutas, verduras, café, pollo plancha, yogur, pescado fresco)
  * medio: 300-700mg (pan, queso fresco, huevos, plato casero normal, legumbres)
  * alto: >700mg (embutidos, jamón, quesos curados, patatas de bolsa, fast food, pizza, restaurante, precocinados, soja, aperitivos)
FORMATO ENTRADA:
{csv_text}
FORMATO SALIDA: CSV con columnas: fecha,hora,descripcion,calorias,carbohidratos_g,proteinas_g,sodio_nivel
Sin texto adicional. Solo el CSV."""
    response = model.generate_content(prompt)
    raw = re.sub(r"^```.*?\n|\n```$", "", response.text.strip(), flags=re.DOTALL)
    df_est = pd.read_csv(StringIO(raw))
    df_est.columns = ["Fecha","hora","comida","calorías_estimadas","carbohidratos_g","proteinas_g","sodio_nivel"]
    df_est["Fecha"] = pd.to_datetime(df_est["Fecha"]).dt.date
    df_est["carbohidratos_g"] = pd.to_numeric(df_est["carbohidratos_g"], errors="coerce")
    df_est["proteinas_g"]     = pd.to_numeric(df_est["proteinas_g"],     errors="coerce")
    keys = ["Fecha","hora","comida"]
    df_out = df_global.merge(
        df_est[keys + ["calorías_estimadas","carbohidratos_g","proteinas_g","sodio_nivel"]],
        on=keys, how="left", suffixes=("","_new")
    )
    df_out["calorías_estimadas"] = df_out["calorías_estimadas_new"].fillna(df_out["calorías_estimadas"])
    for col in ["carbohidratos_g","proteinas_g","sodio_nivel"]:
        df_out[col] = df_out[col+"_new"].combine_first(df_out[col])
    df_out = df_out.drop(columns=[c for c in df_out.columns if c.endswith("_new")])
    if save:
        save_data(df_out, "Estimar calorías y macros")
        st.cache_data.clear()
    return df_out, len(pendientes)

# ---------------- MENU VISUAL ----------------

_prev_menu = st.session_state.get("_prev_menu")

_menu_val = option_menu(
    menu_title=None,
    options=["Hoy", "Rutinas", "Pega tu semana", "Registro", "Evolución", "Modelo"],
    icons=["sun", "repeat", "calendar-week", "list-ul", "graph-up", "cpu"],
    default_index=0,
    orientation="horizontal",
    styles={
        "container":         {"padding": "4px 8px", "background-color": "#FFFFFF"},
        "icon":              {"color": "#8E8E93",  "font-size": "15px"},
        "nav-link":          {"font-size": "13px", "font-weight": "500",
                              "color": "#3C3C43",  "padding": "8px 10px",
                              "border-radius": "8px"},
        "nav-link-selected": {"background-color": "#F2F2F7", "color": "#007AFF",
                              "font-weight": "600"},
    },
)

_user_clicked = _prev_menu is not None and _menu_val != _prev_menu
st.session_state["_prev_menu"] = _menu_val

if _user_clicked:
    st.session_state.pop("nav_page", None)
    pagina = _menu_val
elif "nav_page" in st.session_state:
    pagina = st.session_state["nav_page"]
else:
    pagina = _menu_val

# ---------------- PÁGINA 1 ----------------
if pagina == "Hoy":
    st.title("Hoy")
    if "dia_seleccionado" not in st.session_state:
        st.session_state.dia_seleccionado = date.today()

    if st.session_state.dia_seleccionado == date.today():
        st.caption(date.today().strftime("%A, %d de %B"))
    with st.expander("Ver otro día", expanded=st.session_state.dia_seleccionado != date.today()):
        dia = st.date_input("Día del registro", st.session_state.dia_seleccionado, key="selector_dia_hoy")
        if dia != st.session_state.dia_seleccionado:
            st.session_state.dia_seleccionado = dia
            st.rerun()
    dia = st.session_state.dia_seleccionado
    df_dia = df[df["Fecha"] == dia].copy()
    consumidas = float(df_dia["calorías_estimadas"].sum())
    porcentaje = min(consumidas / objetivo, 1.0)
    st.markdown(f"**{consumidas:.0f} / {objetivo} kcal**")
    color = "#34C759" if porcentaje < 0.8 else "#FF9F0A" if porcentaje < 1.0 else "#FF3B30"
    st.markdown(f'''<div style="background:#E5E5EA;border-radius:8px;height:9px;margin:8px 0 18px"><div style="background:{color};width:{porcentaje*100:.1f}%;height:9px;border-radius:8px"></div></div>''', unsafe_allow_html=True)

    for momento in MOMENTOS:
        bloque = df_dia[df_dia["momento"] == momento]
        kcal_momento = float(bloque["calorías_estimadas"].sum()) if not bloque.empty else 0
        with st.container(border=True):
            st.markdown(f"**{momento}**  ·  {kcal_momento:.0f} kcal")
            if not bloque.empty:
                for idx, row in bloque.iterrows():
                    c1, c2 = st.columns([6, 1])
                    with c1:
                        st.write(f"{row['comida']}  ·  {float(row['calorías_estimadas']):.0f} kcal")
                    with c2:
                        if st.button("×", key=f"del_{idx}", help="Eliminar esta comida"):
                            df = df.drop(index=idx)
                            save_data(df, "Eliminar comida")
                            st.cache_data.clear()
                            st.rerun()
            opciones = [r for r in rutinas if r.get("momento") == momento and _rutina_aplica(r, dia)]
            if opciones:
                st.caption("Rutinas previstas · activa el interruptor cuando las hayas hecho")
                for rutina in opciones:
                    rutina_id = rutina["id"]
                    filas_rutina = df_dia[df_dia.get("rutina_id", pd.Series(index=df_dia.index, dtype=str)).astype(str) == rutina_id]
                    realizada = not filas_rutina.empty
                    total_rutina = sum(float(it.get("kcal", 0) or 0) for it in rutina.get("items", []))
                    toggle_key = f"rutina_toggle_{dia}_{rutina_id}"
                    activada = st.checkbox(
                        f"{rutina['nombre']} · {total_rutina:.0f} kcal",
                        value=realizada,
                        key=toggle_key,
                        help="Al activarla se añaden todos sus alimentos al registro; al desactivarla se eliminan."
                    )
                    if activada != realizada:
                        if activada:
                            df = _registrar_rutina(df, rutina, dia)
                            save_data(df, f"Registrar rutina: {rutina['nombre']}")
                        else:
                            df = df[~((df["Fecha"] == dia) & (df["rutina_id"].astype(str) == rutina_id))].copy()
                            save_data(df, f"Deshacer rutina: {rutina['nombre']}")
                        st.session_state.pop(toggle_key, None)
                        st.cache_data.clear()
                        st.rerun()
                    with st.expander(f"Ver alimentos · {rutina['nombre']}"):
                        for item in rutina.get("items", []):
                            kcal_item = float(item.get("kcal", 0) or 0)
                            st.caption(f"• {item['descripcion']} — {kcal_item:.0f} kcal")
            with st.expander(f"+ Añadir a {momento}"):
                with st.form(f"add_{momento}"):
                    descripcion = st.text_input("Qué has comido", key=f"desc_{momento}")
                    kcal = st.number_input("Calorías (0 = estimar después)", min_value=0, step=10, key=f"kcal_{momento}")
                    guardar = st.form_submit_button("Guardar comida", use_container_width=True)
                if guardar:
                    if not descripcion.strip():
                        st.warning("Escribe una descripción.")
                    else:
                        nueva = _empty_food_row(dia, momento, descripcion.strip(), kcal)
                        df = pd.concat([df, pd.DataFrame([nueva])], ignore_index=True)
                        save_data(df, "Añadir comida")
                        st.cache_data.clear()
                        st.rerun()

    # Contadores rápidos de bebidas: quedan pendientes de estimación nutricional.
    if st.session_state.pop("reset_contadores_bebida", False):
        st.session_state["contador_cerveza"] = 0
        st.session_state["contador_whisky"] = 0
    with st.container(border=True):
        st.markdown("**Bebidas rápidas**")
        st.caption("Se registran como entradas independientes para que Gemini estime sus calorías.")
        bebida_momento = st.selectbox("Momento", MOMENTOS, index=3, key="bebida_momento")
        b1, b2 = st.columns(2)
        with b1:
            cervezas = st.number_input("🍺 Cervezas", min_value=0, max_value=20, step=1, key="contador_cerveza")
        with b2:
            whiskies = st.number_input("🥃 Whisky con Coca-Cola Zero", min_value=0, max_value=20, step=1, key="contador_whisky")
        if st.button("Registrar bebidas", use_container_width=True, disabled=(cervezas + whiskies == 0)):
            nuevas = []
            if cervezas:
                nuevas.append(_empty_food_row(dia, bebida_momento, f"{int(cervezas)} cerveza(s)", 0))
            if whiskies:
                nuevas.append(_empty_food_row(dia, bebida_momento, f"{int(whiskies)} whisky(s) con Coca-Cola Zero", 0))
            df = pd.concat([df, pd.DataFrame(nuevas)], ignore_index=True)
            save_data(df, "Registrar bebidas")
            st.cache_data.clear()
            st.session_state["reset_contadores_bebida"] = True
            st.rerun()

    # Guardar una comida registrada como rutina sencilla.
    with st.expander("Guardar una comida como rutina"):
        if df_dia.empty:
            st.caption("Registra primero una comida para convertirla en rutina.")
        else:
            indices = df_dia.index.tolist()
            seleccion = st.selectbox("Comida", indices, format_func=lambda i: f"{df.loc[i, 'momento']} · {df.loc[i, 'comida']}")
            nombre_rutina = st.text_input("Nombre de la rutina", value=str(df.loc[seleccion, "comida"])[:50])
            dias_guardar = st.multiselect("Días habituales", ["L", "M", "X", "J", "V", "S", "D"], default=["L", "M", "X", "J", "V"])
            if st.button("Guardar rutina", key="guardar_rutina"):
                row = df.loc[seleccion]
                nombre = nombre_rutina.strip() or str(row["comida"])
                rutina = {
                    "id": uuid.uuid4().hex, "nombre": nombre,
                    "momento": row["momento"], "dias_semana": [["L", "M", "X", "J", "V", "S", "D"].index(d) for d in dias_guardar],
                    "items": [{
                        "descripcion": str(row["comida"]),
                        "kcal": float(row["calorías_estimadas"] or 0),
                        "carbohidratos_g": None if pd.isna(row.get("carbohidratos_g")) else float(row["carbohidratos_g"]),
                        "proteinas_g": None if pd.isna(row.get("proteinas_g")) else float(row["proteinas_g"]),
                        "sodio_nivel": None if pd.isna(row.get("sodio_nivel")) else str(row["sodio_nivel"]),
                    }]
                }
                rutinas = [r for r in rutinas if r.get("nombre") != nombre]
                rutinas.append(rutina)
                save_routines(rutinas)
                st.success("Rutina guardada.")
                st.rerun()

    with st.expander("Estimar comidas pendientes"):
        pendientes = int((df_dia["calorías_estimadas"] == 0).sum())
        st.caption(f"{pendientes} entrada(s) pendientes en este día.")
        if st.button("Estimar las pendientes de este día", disabled=pendientes == 0):
            with st.spinner("Estimando calorías y macros…"):
                df_estimado, n = _run_estimacion(df[df["Fecha"] == dia].copy(), save=False)
                otros = df[df["Fecha"] != dia]
                df = pd.concat([otros, df_estimado], ignore_index=True)
                save_data(df, "Estimar comidas del día")
            st.cache_data.clear()
            st.rerun()

elif pagina == "Rutinas":
    st.title("Rutinas")
    st.write("Configura hábitos que se repiten en determinados días. En **Hoy**, aparecerán como interruptores Sí/No; al activarlos se registran todos sus alimentos.")

    DIAS_LABEL = ["L", "M", "X", "J", "V", "S", "D"]
    opciones_edicion = ["＋ Crear nueva rutina"] + [r["nombre"] for r in rutinas]
    seleccion_rutina = st.selectbox("Rutina", opciones_edicion, key="selector_editar_rutina")
    editando = seleccion_rutina != "＋ Crear nueva rutina"
    rutina_base = next((r for r in rutinas if r["nombre"] == seleccion_rutina), {}) if editando else {}

    with st.form("form_rutina_calendario", clear_on_submit=False):
        nombre = st.text_input("Nombre", value=rutina_base.get("nombre", ""), placeholder="Ej. Media mañana", key=f"rutina_nombre_{rutina_base.get('id', 'nueva')}")
        momento_idx = MOMENTOS.index(rutina_base.get("momento", "Entre horas (antes de comer)")) if rutina_base.get("momento", "Entre horas (antes de comer)") in MOMENTOS else 1
        momento_rutina = st.selectbox("Momento del día", MOMENTOS, index=momento_idx, key=f"rutina_momento_{rutina_base.get('id', 'nueva')}")
        dias_base = [DIAS_LABEL[d] for d in rutina_base.get("dias_semana", [0, 1, 2, 3, 4]) if 0 <= d <= 6]
        dias_rutina = st.multiselect("Se repite estos días", DIAS_LABEL, default=dias_base, key=f"rutina_dias_{rutina_base.get('id', 'nueva')}")
        items_base = rutina_base.get("items", [])
        if items_base:
            tabla_items = pd.DataFrame([{
                "Alimento / cantidad": it.get("descripcion", ""),
                "Kcal": it.get("kcal", 0),
                "Carbohidratos (g)": it.get("carbohidratos_g"),
                "Proteínas (g)": it.get("proteinas_g"),
                "Sodio": it.get("sodio_nivel") or "medio",
            } for it in items_base])
        else:
            tabla_items = pd.DataFrame([{
                "Alimento / cantidad": "", "Kcal": 0,
                "Carbohidratos (g)": None, "Proteínas (g)": None, "Sodio": "medio"
            }])
        st.caption("Añade una fila por alimento. Puedes editar las calorías manualmente; 0 significa que se estimarán al registrarlo en Hoy.")
        tabla_items_editada = st.data_editor(
            tabla_items, num_rows="dynamic", use_container_width=True, hide_index=True,
            column_config={
                "Alimento / cantidad": st.column_config.TextColumn("Alimento / cantidad", required=True),
                "Kcal": st.column_config.NumberColumn("Kcal", min_value=0, step=5, format="%.0f"),
                "Carbohidratos (g)": st.column_config.NumberColumn("Carbohidratos (g)", min_value=0, step=1),
                "Proteínas (g)": st.column_config.NumberColumn("Proteínas (g)", min_value=0, step=1),
                "Sodio": st.column_config.SelectboxColumn("Sodio", options=["bajo", "medio", "alto"]),
            }, key=f"editor_items_rutina_{rutina_base.get('id', 'nueva')}"
        )
        guardar_rutina_form = st.form_submit_button("Guardar rutina", type="primary", use_container_width=True)

    if guardar_rutina_form:
        items_nuevos = []
        for _, it in tabla_items_editada.iterrows():
            descripcion = str(it.get("Alimento / cantidad", "")).strip()
            if not descripcion or descripcion.lower() == "nan":
                continue
            items_nuevos.append({
                "descripcion": descripcion,
                "kcal": (lambda v: 0.0 if pd.isna(v) else float(v))(pd.to_numeric(it.get("Kcal", 0), errors="coerce")),
                "carbohidratos_g": None if pd.isna(it.get("Carbohidratos (g)")) else float(it.get("Carbohidratos (g)")),
                "proteinas_g": None if pd.isna(it.get("Proteínas (g)")) else float(it.get("Proteínas (g)")),
                "sodio_nivel": str(it.get("Sodio", "medio")),
            })
        if not nombre.strip():
            st.error("Pon un nombre a la rutina.")
        elif not dias_rutina:
            st.error("Selecciona al menos un día de la semana.")
        elif not items_nuevos:
            st.error("Añade al menos un alimento.")
        else:
            rutina_nueva = {
                "id": rutina_base.get("id", uuid.uuid4().hex),
                "nombre": nombre.strip(), "momento": momento_rutina,
                "dias_semana": [DIAS_LABEL.index(d) for d in dias_rutina],
                "items": items_nuevos,
            }
            rutinas = [r for r in rutinas if r.get("id") != rutina_nueva["id"] and r.get("nombre") != rutina_nueva["nombre"]]
            rutinas.append(rutina_nueva)
            save_routines(rutinas)
            st.success("Rutina guardada.")
            st.rerun()

    # Acceso rápido a la rutina de ejemplo que describe la usuaria.
    st.divider()
    st.subheader("Plantilla rápida")
    st.caption("Crea una rutina de lunes a viernes para dos cafés con leche medianos y un plátano. Las calorías son orientativas y editables.")
    if st.button("＋ Crear ‘Media mañana (L–V)’", use_container_width=True):
        nombre_plantilla = "Media mañana (L–V)"
        plantilla = {
            "id": uuid.uuid4().hex, "nombre": nombre_plantilla,
            "momento": "Entre horas (antes de comer)", "dias_semana": [0, 1, 2, 3, 4],
            "items": [
                {"descripcion": "2 cafés con leche medianos", "kcal": 140, "carbohidratos_g": None, "proteinas_g": None, "sodio_nivel": "bajo"},
                {"descripcion": "1 plátano mediano", "kcal": 105, "carbohidratos_g": None, "proteinas_g": None, "sodio_nivel": "bajo"},
            ]
        }
        rutinas = [r for r in rutinas if r.get("nombre") != nombre_plantilla]
        rutinas.append(plantilla)
        save_routines(rutinas)
        st.success("Plantilla creada. Puedes ajustar las cantidades y calorías seleccionándola arriba.")
        st.rerun()

    st.divider()
    st.subheader("Tus rutinas")
    if not rutinas:
        st.info("Todavía no tienes rutinas creadas.")
    for rutina in rutinas:
        dias_txt = " ".join(DIAS_LABEL[d] for d in rutina.get("dias_semana", []))
        kcal_total = sum(float(it.get("kcal", 0) or 0) for it in rutina.get("items", []))
        with st.expander(f"{rutina['nombre']} · {rutina['momento']} · {dias_txt} · {kcal_total:.0f} kcal"):
            for it in rutina.get("items", []):
                st.write(f"• {it['descripcion']} — {float(it.get('kcal', 0) or 0):.0f} kcal")
            if st.button("Eliminar rutina", key=f"eliminar_rutina_{rutina['id']}"):
                rutinas = [r for r in rutinas if r.get("id") != rutina["id"]]
                save_routines(rutinas)
                st.rerun()

elif pagina == "Pega tu semana":
    st.title("Pega tu semana")
    st.write("Describe lo que has comido durante la semana. Puedes escribirlo día a día o indicar hábitos repetidos, por ejemplo: *café con leche todos los días*.")
    lunes_default = date.today() - timedelta(days=date.today().weekday())
    lunes = st.date_input("Lunes de la semana", lunes_default, key="semana_lunes")
    texto_semana = st.text_area("Tu semana", height=230, placeholder="Lunes: café con leche y tostada...\nComida: lentejas...\nTodos los días tomo un café a media mañana...")
    if st.button("Interpretar semana con Gemini", type="primary", disabled=not texto_semana.strip()):
        try:
            with st.spinner("Interpretando comidas y estimando nutrientes…"):
                preview = _parse_week_with_gemini(texto_semana, lunes)
            if preview.empty:
                st.warning("No he encontrado comidas en el texto.")
            else:
                st.session_state["preview_semana"] = preview
                st.session_state["preview_semana_lunes"] = lunes
        except Exception as exc:
            st.error(f"No se ha podido interpretar la semana: {exc}")
    if "preview_semana" in st.session_state:
        st.subheader("Revisa y corrige antes de guardar")
        preview = st.session_state["preview_semana"].copy()
        edited_preview = st.data_editor(
            preview,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                "momento": st.column_config.SelectboxColumn("Momento", options=MOMENTOS, required=True),
                "comida": st.column_config.TextColumn("Descripción", required=True),
                "calorías_estimadas": st.column_config.NumberColumn("Kcal", min_value=0),
                "carbohidratos_g": st.column_config.NumberColumn("Carbohidratos (g)", min_value=0),
                "proteinas_g": st.column_config.NumberColumn("Proteínas (g)", min_value=0),
                "sodio_nivel": st.column_config.SelectboxColumn("Sodio", options=["bajo", "medio", "alto"]),
            },
            key="editor_preview_semana",
        )
        if st.button("Guardar semana en el registro", type="primary"):
            if edited_preview.empty or edited_preview["comida"].astype(str).str.strip().eq("").any():
                st.error("La tabla debe contener al menos una comida y ninguna descripción vacía.")
            else:
                edited_preview = edited_preview.copy()
                edited_preview["Fecha"] = pd.to_datetime(edited_preview["Fecha"]).dt.date
                edited_preview["hora"] = edited_preview["momento"].map(HORAS_MOMENTO)
                for col in ["ruta_foto", "calorías_estimadas", "carbohidratos_g", "proteinas_g", "sodio_nivel", "rutina_id"]:
                    if col not in edited_preview.columns:
                        edited_preview[col] = "" if col in ["ruta_foto", "rutina_id"] else 0 if col == "calorías_estimadas" else pd.NA
                cols = ["Fecha", "momento", "hora", "comida", "ruta_foto", "calorías_estimadas", "carbohidratos_g", "proteinas_g", "sodio_nivel", "rutina_id"]
                df_save = pd.concat([df, edited_preview[cols]], ignore_index=True)
                save_data(df_save, "Guardar registro semanal")
                st.cache_data.clear()
                st.session_state.pop("preview_semana", None)
                st.success("Semana guardada correctamente.")
                st.rerun()

elif pagina == "Registro":
    _r_title, _r_btn = st.columns([5, 2])
    _r_title.title("Registro")
    with _r_btn:
        st.write("")  # alinear verticalmente
        if st.button("Estimar calorías", use_container_width=True, type="primary"):
            n_pend = (df["calorías_estimadas"] == 0.0).sum()
            if n_pend == 0:
                st.toast("No hay entradas pendientes de estimar")
            else:
                with st.spinner(f"Estimando {n_pend} entradas…"):
                    df, n = _run_estimacion(df)
                st.toast(f"{n} entradas estimadas")
                st.rerun()

    dias_atras = st.slider("Últimos días", 7, 60, 30)
    hoy = date.today()
    rango = [hoy - pd.Timedelta(days=i) for i in range(dias_atras)]

    dias_con_datos = (
        df.groupby("Fecha")["calorías_estimadas"]
        .agg(n="count", kcal="sum")
        .to_dict("index")
    )

    st.markdown("""
    <style>
    /* Registro: mantener columnas en fila en móvil */
    [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 4px !important; }
    [data-testid="stHorizontalBlock"] > div { min-width: 0 !important; }
    </style>""", unsafe_allow_html=True)

    nombres_dia = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    for dia_r in rango:
        col1, col2, col3 = st.columns([3, 5, 1])
        info = dias_con_datos.get(dia_r)
        label = f"{nombres_dia[dia_r.weekday()]} {dia_r.strftime('%d %b')}"

        with col1:
            if info:
                st.markdown(f'<span style="color:#34C759;font-size:10px;">●</span> **{label}**', unsafe_allow_html=True)
            else:
                st.markdown(f'<span style="color:#C6C6C8;font-size:10px;">●</span> **{label}**', unsafe_allow_html=True)
        with col2:
            if info:
                _kcal = int(info["kcal"])
                _pct  = min(_kcal / objetivo * 100, 100)
                _over = _kcal > objetivo
                _bar  = "#FF3B30" if _over else "#34C759"
                _txt  = "#FF3B30" if _over else "#8E8E93"
                st.markdown(f"""
                <div style="margin-top:6px">
                  <div style="background:#E5E5EA;border-radius:4px;height:5px;overflow:hidden">
                    <div style="background:{_bar};width:{_pct:.1f}%;height:5px;border-radius:4px"></div>
                  </div>
                  <span style="font-size:11px;color:{_txt}">{_kcal} / {objetivo} kcal</span>
                </div>""", unsafe_allow_html=True)
            else:
                st.caption("Sin datos")
        with col3:
            if st.button("Ir", key=f"ir_{dia_r}"):
                st.session_state.dia_seleccionado = dia_r
                st.session_state["nav_page"] = "Hoy"
                st.rerun()

# ---------------- PÁGINA 3 ----------------
elif pagina == "Evolución":
    st.title("Evolución")

    df_peso = load_peso()
    df_cals = df.groupby("Fecha", as_index=False)["calorías_estimadas"].sum()

    df_merged = (
        pd.merge(df_cals, df_peso, on="Fecha", how="outer")
        .sort_values("Fecha")
        .reset_index(drop=True)
    )
    df_merged["Fecha"] = pd.to_datetime(df_merged["Fecha"])

    # ---- Selector de período ----
    PERIODOS = {"1S": 7, "1M": 30, "6M": 182, "1A": 365, "Todo": None}
    if "periodo_peso" not in st.session_state:
        st.session_state["periodo_peso"] = "1S"

    cols_p = st.columns(len(PERIODOS))
    for col, (label, _) in zip(cols_p, PERIODOS.items()):
        with col:
            if st.button(
                label,
                use_container_width=True,
                type="primary" if st.session_state["periodo_peso"] == label else "secondary",
            ):
                st.session_state["periodo_peso"] = label
                st.rerun()

    periodo = st.session_state["periodo_peso"]
    dias = PERIODOS[periodo]
    hoy = pd.Timestamp(date.today())
    df_v = df_merged[df_merged["Fecha"] >= hoy - pd.Timedelta(days=dias)].copy() if dias else df_merged.copy()

    # ── Formateador de fechas en español (sin año) ──────────────────
    _DIAS_ES  = ["L", "M", "X", "J", "V", "S", "D"]
    _MESES_ES = ["enero","febrero","marzo","abril","mayo","junio",
                 "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    def _fmt_es(f):
        t = pd.Timestamp(f)
        return f"{_DIAS_ES[t.weekday()]} {t.day} {_MESES_ES[t.month - 1]}"

    # ---- Agregación según período ----
    if periodo in ["1S", "1M"]:
        df_plot = df_v.rename(columns={"Fecha": "x"}).copy()
        df_plot["x_label"] = df_plot["x"].apply(_fmt_es)
        _x_ord = df_plot["x_label"].tolist()   # orden cronológico para el eje
        kcal_label = "Calorías"
    elif periodo in ["6M", "1A"]:
        df_v["x"] = df_v["Fecha"].dt.to_period("W").apply(lambda p: p.start_time)
        df_plot = df_v.groupby("x", as_index=False).agg(
            calorías_estimadas=("calorías_estimadas", "mean"),
            peso_kg=("peso_kg", "mean"),
        )
        kcal_label = "Calorías medias (semana)"
    else:
        df_v["x"] = df_v["Fecha"].dt.to_period("M").apply(lambda p: p.start_time)
        df_plot = df_v.groupby("x", as_index=False).agg(
            calorías_estimadas=("calorías_estimadas", "mean"),
            peso_kg=("peso_kg", "mean"),
        )
        kcal_label = "Calorías medias (mes)"

    # ---- Métricas de resumen ----
    pesos_v = df_v.dropna(subset=["peso_kg"])
    peso_fin   = pesos_v["peso_kg"].iloc[-1]  if len(pesos_v) >= 1 else None
    peso_ini   = pesos_v["peso_kg"].iloc[0]   if len(pesos_v) >= 2 else None
    kcal_media = df_v["calorías_estimadas"].mean()

    m1, m2, m3 = st.columns(3)
    if peso_fin is not None:
        m1.metric("Peso actual", f"{peso_fin:.1f} kg")
    if peso_ini is not None and peso_fin is not None:
        delta = peso_fin - peso_ini
        m2.metric("Cambio en el período", f"{delta:+.2f} kg")
    if not pd.isna(kcal_media):
        m3.metric("Media calórica", f"{kcal_media:.0f} kcal/día")

    # ---- Gráfica ----
    _diario = periodo in ["1S", "1M"]
    _xc = "x_label" if _diario else "x"   # columna x a usar en trazas

    fig = go.Figure()

    # Barras de calorías
    fig.add_trace(go.Bar(
        x=df_plot[_xc], y=df_plot["calorías_estimadas"],
        name=kcal_label, marker_color="#115a8e", opacity=0.55, yaxis="y1"
    ))
    fig.add_hline(
        y=objetivo, line_dash="dash", line_color="rgba(243,156,18,0.7)",
        annotation_text="Objetivo", annotation_position="top left", yref="y1"
    )

    # Peso
    dp = df_plot.dropna(subset=["peso_kg"])
    fig.add_trace(go.Scatter(
        x=dp[_xc], y=dp["peso_kg"],
        name="Peso (kg)", yaxis="y2",
        line=dict(color="#e74c3c", width=2), mode="lines+markers",
        marker=dict(size=6 if _diario else 4),
    ))

    # Media móvil 7 días (solo en vista diaria con suficientes puntos)
    if _diario and len(dp) >= 5:
        dp = dp.copy()
        dp["rolling"] = dp["peso_kg"].rolling(7, min_periods=2, center=True).mean()
        fig.add_trace(go.Scatter(
            x=dp[_xc], y=dp["rolling"],
            name="Media 7 días", yaxis="y2",
            line=dict(color="#c0392b", dash="dot", width=1.5), mode="lines",
        ))

    # Línea de tendencia (en 6M, 1A, Todo)
    if not _diario and len(dp) >= 3:
        idx_t = np.arange(len(dp))
        tend  = np.poly1d(np.polyfit(idx_t, dp["peso_kg"].values, 1))(idx_t)
        fig.add_trace(go.Scatter(
            x=dp[_xc].values, y=tend,
            name="Tendencia", yaxis="y2",
            line=dict(color="#e74c3c", dash="dash", width=1.5), mode="lines",
        ))

    _xaxis_cfg = dict(
        title="Calorías", showgrid=True, gridcolor="#f0f0f0"
    )
    if _diario:
        _xaxis_cfg = dict(categoryorder="array", categoryarray=_x_ord)

    fig.update_layout(
        xaxis=_xaxis_cfg if _diario else {},
        yaxis=dict(title="Calorías", showgrid=True, gridcolor="#f0f0f0"),
        yaxis2=dict(title="Peso (kg)", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=-0.15, x=0),
        hovermode="x unified",
        margin=dict(l=0, r=10, t=10, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        bargap=0.15,
    )
    if _diario:
        fig.update_xaxes(categoryorder="array", categoryarray=_x_ord)
    st.plotly_chart(fig, use_container_width=True)

# ---------------- PÁGINA 4 (eliminada — Estimación integrada en Registro) ----------------

# ---------------- PÁGINA 5: MODELO DE PESO ----------------
elif pagina == "Modelo":
    _m_title, _m_btn = st.columns([5, 1])
    _m_title.title("Modelo")
    with _m_btn:
        st.write("")
        if st.button("Actualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # ---- Cargar fuentes ----
    df_basal  = load_basal_energy()
    df_activo = load_active_energy()
    df_sleep  = load_sleep_data()
    df_ciclo  = load_ciclo()

    # Peso: primera medición del día (mañana)
    dp_raw = pd.read_csv("data/peso_diario.csv")
    dp_raw["dt"] = pd.to_datetime(dp_raw["Date"])
    dp_raw["Fecha"] = dp_raw["dt"].dt.date
    df_peso = (dp_raw.sort_values("dt")
               .groupby("Fecha", as_index=False).first()
               [["Fecha", "Body mass(kg)"]]
               .rename(columns={"Body mass(kg)": "peso_kg"}))
    df_peso = df_peso.sort_values("Fecha").reset_index(drop=True)

    # ---- Comidas diarias: total + alcohol ----
    _alc_kw = ["cerveza", "vino", "whiskey", "whisky", "gin", "ron", "vodka",
               "copa", "caña", "cubata", "cava", "chupito", "jager", "tequila",
               "licor", "vermut", "sidra"]
    _df = df.copy()
    _df["_alc"] = _df["comida"].str.lower().apply(lambda x: any(k in str(x) for k in _alc_kw))
    _df["_kcal_alc"] = _df["calorías_estimadas"].where(_df["_alc"], 0.0)
    _df["_carbs"] = pd.to_numeric(_df.get("carbohidratos_g", pd.Series(dtype=float)), errors="coerce")
    # Sodio ponderado: "alto"=1.0, "medio"=0.5, "bajo"/otros=0.0.
    # Antes solo se contaba "alto"; "medio" (300-700mg, ver prompt de
    # estimación) quedaba igualado a "bajo". Ver vault/decisiones.md
    # (modelado, 2026-07-19) para la comparación de R² LOO que justifica
    # este cambio.
    _sodio_niv = _df.get("sodio_nivel", pd.Series(dtype=str))
    _df["_sodio_alto"] = np.select(
        [_sodio_niv == "alto", _sodio_niv == "medio"],
        [1.0, 0.5],
        default=0.0,
    )
    _df["_sodio_valido"] = (_df.get("sodio_nivel", pd.Series(dtype=str)).notna() &
                            (_df.get("sodio_nivel", pd.Series(dtype=str)) != "")).astype(float)
    # Hora última comida: horas desde medianoche (0–24)
    _df["_hora_num"] = pd.to_datetime(_df["hora"], format="%H:%M", errors="coerce").dt.hour + \
                       pd.to_datetime(_df["hora"], format="%H:%M", errors="coerce").dt.minute / 60.0
    df_food = _df.groupby("Fecha").agg(
        kcal_total=("calorías_estimadas", "sum"),
        kcal_alcohol=("_kcal_alc", "sum"),
        carbs_total=("_carbs", "sum"),
        sodio_alto_n=("_sodio_alto", "sum"),
        sodio_n=("_sodio_valido", "sum"),
        hora_ultima=("_hora_num", "max"),
    ).reset_index()
    df_food["sodio_alto_frac"] = df_food["sodio_alto_n"] / df_food["sodio_n"].replace(0, np.nan)

    # ---- Tabla diaria maestra ----
    df_e = df_basal.merge(df_activo, on="Fecha", how="outer")
    df_e["gasto"] = (df_e["basal_kcal"].fillna(df_e["basal_kcal"].median()) +
                     df_e["activo_kcal"].fillna(df_e["activo_kcal"].median()))

    df_master = (df_e
        .merge(df_food, on="Fecha", how="left")
        .merge(df_sleep, on="Fecha", how="left")
        .sort_values("Fecha").reset_index(drop=True))
    df_master["superavit"] = df_master["kcal_total"] - df_master["gasto"]

    # Fase del ciclo para cada día
    _res = df_master["Fecha"].apply(lambda f: _fase(f, df_ciclo))
    df_master["dia_ciclo"]    = [r[0] for r in _res]
    df_master["es_menstrual"] = [r[1] for r in _res]
    df_master["es_lutea"]     = [r[2] for r in _res]

    # ---- Construir observaciones: pares de pesadas consecutivas ----
    peso_s = df_peso.sort_values("Fecha").reset_index(drop=True)
    obs = []
    for i in range(len(peso_s) - 1):
        r1, r2 = peso_s.iloc[i], peso_s.iloc[i + 1]
        gap = (r2["Fecha"] - r1["Fecha"]).days
        if not (1 <= gap <= 7):
            continue
        period = df_master[
            (df_master["Fecha"] >= r1["Fecha"]) & (df_master["Fecha"] < r2["Fecha"])
        ]
        dias_comida = (period["kcal_total"].fillna(0) > 0).sum()
        if dias_comida < max(1, gap // 2):
            continue
        food_rows = period[period["kcal_total"].notna() & (period["kcal_total"] > 0)]
        obs.append({
            "fecha": r2["Fecha"],
            "delta_dia": (r2["peso_kg"] - r1["peso_kg"]) / gap,
            "superavit_medio":   food_rows["superavit"].mean() if not food_rows.empty else np.nan,
            "alcohol_medio":     food_rows["kcal_alcohol"].mean() if not food_rows.empty else 0.0,
            "carbs_medio":       food_rows["carbs_total"].mean() if not food_rows.empty else np.nan,
            "sodio_alto_frac":   food_rows["sodio_alto_frac"].mean() if not food_rows.empty else np.nan,
            "hora_ultima_media": food_rows["hora_ultima"].mean() if not food_rows.empty else np.nan,
            "activo_medio":      period["activo_kcal"].mean(),
            "sueño_medio":       period["horas_cama"].mean(),
            "es_lutea":          period["es_lutea"].mean(),
            "es_menstrual":      period["es_menstrual"].mean(),
        })

    df_obs = pd.DataFrame(obs)
    if df_obs.empty:
        st.warning("No hay suficientes datos para construir el modelo.")
        _d1, _d2, _d3, _d4, _d5, _d6 = st.columns(6)
        _d1.metric("comidas.csv", len(df))
        _d2.metric("peso_diario.csv", len(df_peso))
        _d3.metric("basal_energy.csv", len(df_basal))
        _d4.metric("active_energy.csv", len(df_activo))
        _d5.metric("sleep_time.csv", len(df_sleep))
        _d6.metric("ciclo.csv", len(df_ciclo))
        st.stop()

    # ---- Selección de features ----
    # activo_medio NO entra como predictor independiente: ya está restado dentro de superavit_medio.
    # Incluirlo dos veces crea multicolinealidad y el coeficiente aparece con signo incorrecto.
    FEAT = {
        "superavit_medio": "Superávit calórico (kcal/día)",
        "alcohol_medio":   "Calorías alcohol (kcal/día)",
        "es_lutea":        "Fase lútea (fracción del período)",
        "es_menstrual":    "Fase menstrual (fracción del período)",
    }
    n_sueño = df_obs["sueño_medio"].notna().sum()
    if n_sueño >= 10:
        df_obs["sueño_medio"] = df_obs["sueño_medio"].fillna(df_obs["sueño_medio"].median())
        FEAT["sueño_medio"] = "Horas en cama (media del período)"
    n_carbs = df_obs["carbs_medio"].notna().sum()
    if n_carbs >= 20:
        FEAT["carbs_medio"] = "Carbohidratos (g/día)"
    n_sodio = df_obs["sodio_alto_frac"].notna().sum()
    if n_sodio >= 20:
        FEAT["sodio_alto_frac"] = "Fracción días sodio alto"
    n_hora = df_obs["hora_ultima_media"].notna().sum()
    if n_hora >= 10:
        df_obs["hora_ultima_media"] = df_obs["hora_ultima_media"].fillna(df_obs["hora_ultima_media"].median())
        FEAT["hora_ultima_media"] = "Hora última comida (media)"

    feat_keys = list(FEAT.keys())
    df_m = df_obs[feat_keys + ["delta_dia", "fecha"]].dropna(
        subset=feat_keys + ["delta_dia"]
    )

    if len(df_m) < 10:
        st.warning(f"Solo {len(df_m)} observaciones completas. Añade más días con datos de comida.")
        _d1, _d2, _d3, _d4, _d5, _d6 = st.columns(6)
        _d1.metric("comidas.csv", len(df))
        _d2.metric("peso_diario.csv", len(df_peso))
        _d3.metric("basal_energy.csv", len(df_basal))
        _d4.metric("active_energy.csv", len(df_activo))
        _d5.metric("sleep_time.csv", len(df_sleep))
        _d6.metric("ciclo.csv", len(df_ciclo))
        _d1.metric("Obs. modelo (df_obs)", len(df_obs))
        st.stop()

    # ---- Ridge regression (alpha=2.0 para estabilizar coeficientes de ciclo) ----
    X = df_m[feat_keys].values.astype(float)
    y = df_m["delta_dia"].values.astype(float)

    mu    = X.mean(axis=0)
    sigma = X.std(axis=0)
    sigma[sigma == 0] = 1.0
    Xs = np.column_stack([np.ones(len(X)), (X - mu) / sigma])

    alpha_r = 2.0
    I_reg = np.diag([0.0] + [1.0] * len(feat_keys))

    def _ridge(Xs_, y_, alpha_):
        A = Xs_.T @ Xs_ + alpha_ * np.diag([0.0] + [1.0] * (Xs_.shape[1] - 1))
        return np.linalg.solve(A, Xs_.T @ y_)

    w = _ridge(Xs, y, alpha_r)
    y_hat  = Xs @ w
    ss_res = ((y - y_hat) ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2     = float(max(0.0, 1.0 - ss_res / ss_tot))
    rmse   = float(np.sqrt(ss_res / len(y)))

    # LOO cross-validation (R² real sobre datos no vistos)
    y_loo = np.zeros(len(y))
    for _i in range(len(y)):
        _mask = np.ones(len(y), dtype=bool); _mask[_i] = False
        _w = _ridge(Xs[_mask], y[_mask], alpha_r)
        y_loo[_i] = Xs[_i] @ _w
    r2_loo = float(max(0.0, 1.0 - ((y - y_loo)**2).sum() / ss_tot))

    # ---- Métricas ----
    st.caption(
        f"**{len(df_m)}** pares de pesadas consecutivas (≤7 días) con datos de comida · "
        f"Sueño disponible en {n_sueño} períodos"
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("R² (ajuste)", f"{r2:.2f}",
              help="Varianza de Δpeso explicada sobre los datos de entrenamiento.")
    c2.metric("R² (LOO)", f"{r2_loo:.2f}",
              help="R² real estimado mediante leave-one-out. Si es mucho menor que R² ajuste, hay sobreajuste.")
    c3.metric("Error típico", f"±{rmse * 1000:.0f} g/día")
    c4.metric("Observaciones", len(df_m))

    # ---- Predicción para mañana ----
    st.divider()
    st.subheader("Predicción para mañana")
    hoy_p    = date.today()
    manana_p = hoy_p + timedelta(days=1)
    ultimo_p = df_peso.sort_values("Fecha").iloc[-1]
    f_ult    = ultimo_p["Fecha"]
    gap_p    = (manana_p - f_ult).days
    dias_desde = (hoy_p - f_ult).days

    if gap_p > 7:
        st.info(
            f"Tu última pesada fue hace **{dias_desde} días** ({f_ult}). "
            "Pésate primero para activar la predicción (máx. 7 días de ventana)."
        )
    else:
        pred_period = df_master[
            (df_master["Fecha"] >= f_ult) & (df_master["Fecha"] < manana_p)
        ]
        pred_food = pred_period[
            pred_period["kcal_total"].notna() & (pred_period["kcal_total"] > 0)
        ]
        dias_comida    = len(pred_food)
        dias_esperados = dias_desde + 1  # días de comida en ventana (hoy incluido)

        fp = pred_food
        _sup = fp["superavit"].mean()    if not fp.empty else np.nan
        _alc = fp["kcal_alcohol"].mean() if not fp.empty else 0.0

        _fases_v = [_fase((pd.Timestamp(f_ult) + pd.Timedelta(days=d)).date(), df_ciclo)
                    for d in range(gap_p)]
        _lut  = float(np.mean([v[2] for v in _fases_v]))
        _mens = float(np.mean([v[1] for v in _fases_v]))

        x_pred_map = {
            "superavit_medio": _sup  if not pd.isna(_sup)  else float(df_m["superavit_medio"].mean()),
            "alcohol_medio":   _alc,
            "es_lutea":        _lut,
            "es_menstrual":    _mens,
        }
        if "sueño_medio" in feat_keys:
            sv = pred_period["horas_cama"].mean()
            x_pred_map["sueño_medio"] = sv if not pd.isna(sv) else float(df_m["sueño_medio"].median())
        if "carbs_medio" in feat_keys:
            cv = fp["carbs_total"].mean() if not fp.empty else np.nan
            x_pred_map["carbs_medio"] = cv if not pd.isna(cv) else float(df_m["carbs_medio"].median())
        if "sodio_alto_frac" in feat_keys:
            sv2 = fp["sodio_alto_frac"].mean() if not fp.empty else np.nan
            x_pred_map["sodio_alto_frac"] = sv2 if not pd.isna(sv2) else float(df_m["sodio_alto_frac"].median())
        if "hora_ultima_media" in feat_keys:
            hv = fp["hora_ultima"].mean() if not fp.empty else np.nan
            x_pred_map["hora_ultima_media"] = hv if not pd.isna(hv) else float(df_m["hora_ultima_media"].median())

        x_arr = np.array([x_pred_map[k] for k in feat_keys])
        x_s   = np.concatenate([[1.0], (x_arr - mu) / sigma])
        delta_pred = float(x_s @ w)
        peso_pred  = float(ultimo_p["peso_kg"]) + delta_pred * gap_p

        pa, pb, pc = st.columns(3)
        pa.metric(
            "Última pesada",
            f"{float(ultimo_p['peso_kg']):.2f} kg",
            f"hace {dias_desde}d" if dias_desde > 0 else "hoy"
        )
        pb.metric(
            "Peso estimado mañana",
            f"{peso_pred:.2f} kg",
            f"{delta_pred * gap_p * 1000:+.0f} g"
        )
        if dias_comida == 0:
            pc.warning(f"Sin comidas desde {f_ult} — usando superávit medio histórico como base")
        elif dias_comida < dias_esperados:
            pc.warning(f"Datos parciales: {dias_comida}/{dias_esperados} días con comidas")
        else:
            pc.success(f"{dias_comida} día(s) de comidas analizados")
    st.divider()

    # ---- Tabla de coeficientes ----
    st.subheader("Factores de peso")
    coef_norm = w[1:]
    coef_orig = coef_norm / sigma
    df_coef = pd.DataFrame({
        "Variable": [FEAT[k] for k in feat_keys],
        "Efecto por unidad → g/día": np.round(coef_orig * 1000, 2),
        "Importancia relativa (%)":  np.round(np.abs(coef_norm) / np.abs(coef_norm).sum() * 100, 1),
    }).sort_values("Importancia relativa (%)", ascending=False).reset_index(drop=True)
    st.dataframe(df_coef, use_container_width=True)
    st.caption(
        "Para las variables de ciclo (fracción 0–1): el efecto es el máximo al pasar el período entero en esa fase."
    )

    # ---- Gráfica predicción vs real (último mes) ----
    st.subheader("Predicción vs real")
    cutoff_30 = date.today() - pd.Timedelta(days=30)
    mask_30 = np.array([f >= cutoff_30 for f in df_m["fecha"]])
    if mask_30.sum() < 3:
        st.caption("Menos de 3 observaciones en el último mes — mostrando histórico completo.")
        mask_30 = np.ones(len(df_m), dtype=bool)
    fechas_30 = [f for f, m in zip(df_m["fecha"].tolist(), mask_30) if m]
    y_30      = y[mask_30]
    yhat_30   = y_hat[mask_30]
    fig_m = go.Figure()
    fig_m.add_trace(go.Scatter(
        x=fechas_30, y=(y_30 * 1000).tolist(),
        name="Δ Peso real (g/día)", mode="lines+markers", line=dict(color="#e74c3c")
    ))
    fig_m.add_trace(go.Scatter(
        x=fechas_30, y=(yhat_30 * 1000).tolist(),
        name="Δ Peso estimado (g/día)", mode="lines+markers",
        line=dict(color="#115a8e", dash="dash")
    ))
    fig_m.add_hline(y=0, line_dash="dot", line_color="gray")
    fig_m.update_layout(
        yaxis_title="g/día", hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5),
        margin=dict(b=60),
    )
    st.plotly_chart(fig_m, use_container_width=True)

    # ---- Tendencia mensual de features ----
    st.subheader("Tendencia mensual")

    _dt = df_master.copy()
    _dt["mes"] = pd.to_datetime(_dt["Fecha"]).dt.to_period("M").dt.to_timestamp()

    _food_mes = (_dt[_dt["kcal_total"].notna() & (_dt["kcal_total"] > 0)]
                 .groupby("mes").agg(
                     superavit_medio=("superavit",      "mean"),
                     carbs_medio    =("carbs_total",    "mean"),
                     sodio_alto_frac=("sodio_alto_frac","mean"),
                     n_dias         =("kcal_total",     "count"),
                 ).reset_index())
    _food_mes = _food_mes[_food_mes["n_dias"] >= 5]

    _peso_mes = (df_peso
                 .assign(mes=pd.to_datetime(df_peso["Fecha"]).dt.to_period("M").dt.to_timestamp())
                 .groupby("mes")["peso_kg"].mean().reset_index())

    _trend = _food_mes.merge(_peso_mes, on="mes", how="inner")

    if len(_trend) < 2:
        st.info("No hay suficientes meses con datos para mostrar la tendencia.")
    else:
        # Peso mensual
        fig_tw = go.Figure()
        fig_tw.add_trace(go.Scatter(
            x=_trend["mes"], y=_trend["peso_kg"].round(2),
            mode="lines+markers", line=dict(color="#2c3e50", width=2),
        ))
        fig_tw.update_layout(yaxis_title="kg", height=200,
                              margin=dict(t=10, b=10, l=0, r=0),
                              hovermode="x unified")
        st.caption("Peso medio mensual")
        st.plotly_chart(fig_tw, use_container_width=True)

        # Features más importantes del modelo, de 2 en 2
        _candidates = [
            ("superavit_medio",  "Superávit calórico (kcal/día)", "#e74c3c"),
            ("carbs_medio",      "Carbohidratos (g/día)",         "#f39c12"),
            ("sodio_alto_frac",  "Fracción sodio alto",           "#9b59b6"),
        ]
        _feats_plot = [("superavit_medio", "Superávit calórico (kcal/día)", "#e74c3c")] + [
            (k, l, c) for k, l, c in _candidates[1:]
            if k in feat_keys and k in _trend.columns and _trend[k].notna().sum() >= 2
        ]

        for _i in range(0, len(_feats_plot), 2):
            _cols = st.columns(2)
            for _j in range(2):
                if _i + _j >= len(_feats_plot):
                    break
                _key, _label, _color = _feats_plot[_i + _j]
                _vals = _trend[_key].dropna()
                if len(_vals) < 2:
                    continue
                _media = float(_vals.mean())
                _fig_f = go.Figure()
                _fig_f.add_trace(go.Scatter(
                    x=_trend["mes"], y=_trend[_key].round(1),
                    mode="lines+markers", line=dict(color=_color, width=2),
                ))
                _fig_f.add_hline(y=_media, line_dash="dot", line_color="gray",
                                  annotation_text=f"media {_media:.0f}",
                                  annotation_position="bottom right")
                _fig_f.update_layout(
                    height=200, margin=dict(t=10, b=10, l=0, r=0),
                    hovermode="x unified", showlegend=False,
                )
                with _cols[_j]:
                    st.caption(_label)
                    st.plotly_chart(_fig_f, use_container_width=True)

        st.caption(
            "Cada punto = media mensual de días con comida registrada (mín. 5 días/mes). "
            "Superávit negativo = déficit calórico → baja peso. "
            "Compara la dirección de cada feature con la curva de peso de arriba."
        )

    # ---- Contribution plot mensual ----
    st.subheader("Contribuciones")
    st.caption(
        "Barras apiladas: cuánto aporta cada variable al Δpeso predicho (g/día). "
        "Hacia arriba = empuja a subir peso; hacia abajo = a bajarlo. "
        "La línea negra es el Δpeso real observado mensual."
    )

    _dm2 = df_m.copy()
    _dm2["mes"]          = pd.to_datetime(_dm2["fecha"]).dt.to_period("M").dt.to_timestamp()
    _dm2["delta_real_g"] = y * 1000

    # Descomposición: baseline (predicción cuando features = 0) + contribución absoluta de cada feature
    _intercept_adj = (float(w[0]) - float(np.dot(coef_orig, mu))) * 1000  # g/día, constante

    for _ki, _k in enumerate(feat_keys):
        _dm2[f"_c_{_k}"] = coef_orig[_ki] * _dm2[_k].fillna(mu[_ki]) * 1000

    _ccols2 = [f"_c_{k}" for k in feat_keys]
    _dm2_mes  = _dm2.groupby("mes")[_ccols2 + ["delta_real_g"]].mean().reset_index()
    _counts2  = _dm2.groupby("mes")["delta_real_g"].count().reset_index(name="n_obs")
    _dm2_mes  = _dm2_mes.merge(_counts2, on="mes")
    _dm2_mes  = _dm2_mes[_dm2_mes["n_obs"] >= 2].reset_index(drop=True)

    _FEAT_COLORS = {
        "superavit_medio":   "#e74c3c",
        "carbs_medio":       "#f39c12",
        "sodio_alto_frac":   "#2980b9",
        "hora_ultima_media": "#27ae60",
        "alcohol_medio":     "#8e44ad",
        "sueño_medio":       "#16a085",
        "es_lutea":          "#e67e22",
        "es_menstrual":      "#c0392b",
    }

    if len(_dm2_mes) >= 2:
        fig_cp = go.Figure()

        # Baseline (intercepto ajustado, constante)
        fig_cp.add_trace(go.Bar(
            x=_dm2_mes["mes"],
            y=[_intercept_adj] * len(_dm2_mes),
            name="Baseline",
            marker_color="#bdc3c7",
            opacity=0.7,
        ))

        # Contribución de cada feature
        for _k in feat_keys:
            fig_cp.add_trace(go.Bar(
                x=_dm2_mes["mes"],
                y=_dm2_mes[f"_c_{_k}"].round(1),
                name=FEAT[_k],
                marker_color=_FEAT_COLORS.get(_k, "#95a5a6"),
            ))

        # Δpeso real observado
        fig_cp.add_trace(go.Scatter(
            x=_dm2_mes["mes"],
            y=_dm2_mes["delta_real_g"].round(1),
            mode="lines+markers",
            name="Δ Peso real",
            line=dict(color="#2c3e50", width=2.5),
            marker=dict(size=6),
        ))

        fig_cp.add_hline(y=0, line_dash="dot", line_color="gray")
        fig_cp.update_layout(
            barmode="relative",
            yaxis_title="g/día",
            hovermode="x unified",
            height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=60, b=20, l=0, r=0),
        )
        st.plotly_chart(fig_cp, use_container_width=True)
    else:
        st.info("No hay suficientes meses con datos para mostrar la descomposición.")