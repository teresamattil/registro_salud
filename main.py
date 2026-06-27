import streamlit as st
import pandas as pd
import numpy as np
import requests
import base64
from datetime import date, datetime
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
from io import StringIO
import re
from streamlit_option_menu import option_menu

st.set_page_config(page_title="Diario de comidas", layout="wide")

REPO = "teresamattil/registro_salud"
FILE = "comidas.csv"
API_URL = f"https://api.github.com/repos/{REPO}/contents/{FILE}"
TOKEN = st.secrets["GITHUB_TOKEN"]
GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
HEADERS = {"Authorization": f"token {TOKEN}"}
objetivo = 1500  # Calorías diarias objetivo

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-3-flash-preview")

@st.cache_data(ttl=60)
def load_data():
    r = requests.get(API_URL, headers=HEADERS).json()
    if "content" not in r:
        return pd.DataFrame(columns=["Fecha","hora","comida","ruta_foto","calorías_estimadas",
                                      "carbohidratos_g","proteinas_g","sodio_nivel"])
    content = base64.b64decode(r["content"])
    d = pd.read_csv(pd.io.common.BytesIO(content))
    for col in ["carbohidratos_g", "proteinas_g", "sodio_nivel"]:
        if col not in d.columns:
            d[col] = pd.NA
    return d

def save_data(df, message):
    r_api = requests.get(API_URL, headers=HEADERS).json()
    sha = r_api["sha"]
    content = base64.b64encode(df.to_csv(index=False).encode()).decode()
    requests.put(API_URL, headers=HEADERS, json={"message": message, "content": content, "sha": sha})

@st.cache_data
def load_peso():
    dp = pd.read_csv("data/peso_diario.csv")
    dp["Date"] = pd.to_datetime(dp["Date"]).dt.date
    dp = dp.groupby("Date", as_index=False)["Body mass(kg)"].mean()
    dp.columns = ["Fecha", "peso_kg"]
    return dp

@st.cache_data
def load_basal_energy():
    d = pd.read_csv("data/basal_energy.csv")
    d["Fecha"] = pd.to_datetime(d["Date"]).dt.date
    d["basal_kcal"] = d["Basal energy burned(kcal)"]
    return d[["Fecha", "basal_kcal"]]

@st.cache_data
def load_active_energy():
    d = pd.read_csv("data/active_energy.csv")
    d["Fecha"] = pd.to_datetime(d["Date"]).dt.date
    d["activo_kcal"] = pd.to_numeric(d["Active energy burned(kcal)"], errors="coerce")
    return d[["Fecha", "activo_kcal"]]

@st.cache_data
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

@st.cache_data
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

df = load_data()
df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date

# ---------------- MENU VISUAL ----------------

_prev_menu = st.session_state.get("_prev_menu")

_menu_val = option_menu(
    menu_title=None,
    options=["Resumen diario", "Registro", "Peso & Calorías", "Estimación", "Modelo de peso"],
    icons=["calendar-check", "calendar3", "speedometer2", "lightning-fill", "bar-chart-line"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
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
if pagina == "Resumen diario":
    st.title("🍽️ Diario de comidas")

    if "dia_seleccionado" not in st.session_state:
        st.session_state.dia_seleccionado = date.today()

    dia = st.date_input("Día", st.session_state.dia_seleccionado)
    st.session_state.dia_seleccionado = dia

    # Datos del día
    df_dia = df[df["Fecha"] == dia].copy()
    consumidas = df_dia["calorías_estimadas"].sum()
    porcentaje = min(consumidas / objetivo, 1.0)

    st.markdown(f"**Calorías consumidas:** {consumidas} / {objetivo} kcal")
    color = "#2ecc71" if porcentaje < 0.8 else "#f39c12" if porcentaje < 1.0 else "#e74c3c"
    st.markdown(f"""
    <div style="background:#e0e0e0;border-radius:6px;height:20px;margin-bottom:1rem">
      <div style="background:{color};width:{min(porcentaje,1)*100:.1f}%;height:20px;border-radius:6px;transition:width .3s"></div>
    </div>""", unsafe_allow_html=True)

    # Tabla editable con checkbox para borrar
    df_edit = df_dia[["Fecha", "hora", "comida", "calorías_estimadas"]].copy()
    df_edit.insert(0, "Borrar", False)

    edited = st.data_editor(
        df_edit,
        use_container_width=True,
        num_rows="fixed",
        key="editor_dia"
    )

    if st.button("Editar (borrar seleccionados)"):
        idx_borrar = edited[edited["Borrar"]].index
        if len(idx_borrar) == 0:
            st.info("No has seleccionado ninguna fila")
            st.stop()

        # Eliminar del dataframe global usando los índices reales
        df = df.drop(idx_borrar)
        save_data(df, "Borrar comidas")

        st.cache_data.clear()
        st.rerun()

    # ---- Añadir comida ----
    if "hora_seleccionada" not in st.session_state:
        st.session_state.hora_seleccionada = datetime.utcnow().time()

    with st.form("add_food"):
        f = st.date_input("Fecha", st.session_state.dia_seleccionado)
        h = st.time_input("Hora", st.session_state.hora_seleccionada)
        c = st.text_input("Comida")
        k = st.number_input("Calorías estimadas", min_value=0)
        submit = st.form_submit_button("Guardar")

    if submit:
        if not c:
            st.warning("El nombre de la comida no puede estar vacío")
            st.stop()
        st.session_state.hora_seleccionada = h
        new_row = {
            "Fecha": f,
            "hora": h.strftime("%H:%M"),
            "comida": c,
            "calorías_estimadas": k
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df, "Añadir comida")

        st.cache_data.clear()
        st.rerun()

# ---------------- PÁGINA 2 ----------------
elif pagina == "Registro":
    st.title("📋 Registro de días")

    dias_atras = st.slider("Últimos días", 7, 60, 30)
    hoy = date.today()
    rango = [hoy - pd.Timedelta(days=i) for i in range(dias_atras)]

    dias_con_datos = (
        df.groupby("Fecha")["calorías_estimadas"]
        .agg(n="count", kcal="sum")
        .to_dict("index")
    )

    nombres_dia = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    for dia_r in rango:
        col1, col2, col3 = st.columns([2, 4, 1])
        info = dias_con_datos.get(dia_r)
        label = f"{nombres_dia[dia_r.weekday()]} {dia_r.strftime('%d %b')}"

        with col1:
            if info:
                st.markdown(f"✅ **{label}**")
            else:
                st.markdown(f"❌ **{label}**")
        with col2:
            if info:
                st.caption(f"{info['n']} comidas · {int(info['kcal'])} kcal")
            else:
                st.caption("Sin datos")
        with col3:
            if st.button("Ir", key=f"ir_{dia_r}"):
                st.session_state.dia_seleccionado = dia_r
                st.session_state["nav_page"] = "Resumen diario"
                st.rerun()

# ---------------- PÁGINA 3 ----------------
elif pagina == "Peso & Calorías":
    st.title("⚖️ Peso & Calorías")

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
        st.session_state["periodo_peso"] = "1M"

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

    # ---- Agregación según período ----
    if periodo in ["1S", "1M"]:
        df_plot = df_v.rename(columns={"Fecha": "x"})
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
    fig = go.Figure()

    # Barras de calorías
    fig.add_trace(go.Bar(
        x=df_plot["x"], y=df_plot["calorías_estimadas"],
        name=kcal_label, marker_color="#115a8e", opacity=0.55, yaxis="y1"
    ))
    fig.add_hline(
        y=objetivo, line_dash="dash", line_color="rgba(243,156,18,0.7)",
        annotation_text="Objetivo", annotation_position="top left", yref="y1"
    )

    # Peso
    dp = df_plot.dropna(subset=["peso_kg"])
    fig.add_trace(go.Scatter(
        x=dp["x"], y=dp["peso_kg"],
        name="Peso (kg)", yaxis="y2",
        line=dict(color="#e74c3c", width=2), mode="lines+markers",
        marker=dict(size=4 if periodo not in ["1S", "1M"] else 6),
    ))

    # Media móvil 7 días (solo en vista diaria con suficientes puntos)
    if periodo in ["1S", "1M"] and len(dp) >= 5:
        dp = dp.copy()
        dp["rolling"] = dp["peso_kg"].rolling(7, min_periods=2, center=True).mean()
        fig.add_trace(go.Scatter(
            x=dp["x"], y=dp["rolling"],
            name="Media 7 días", yaxis="y2",
            line=dict(color="#c0392b", dash="dot", width=1.5), mode="lines",
        ))

    # Línea de tendencia (en 6M, 1A, Todo)
    if periodo not in ["1S", "1M"] and len(dp) >= 3:
        idx_t = np.arange(len(dp))
        tend  = np.poly1d(np.polyfit(idx_t, dp["peso_kg"].values, 1))(idx_t)
        fig.add_trace(go.Scatter(
            x=dp["x"].values, y=tend,
            name="Tendencia", yaxis="y2",
            line=dict(color="#e74c3c", dash="dash", width=1.5), mode="lines",
        ))

    fig.update_layout(
        yaxis=dict(title="Calorías", showgrid=True, gridcolor="#f0f0f0"),
        yaxis2=dict(title="Peso (kg)", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=-0.15, x=0),
        hovermode="x unified",
        margin=dict(l=0, r=10, t=10, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        bargap=0.15,
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------- PÁGINA 4 ----------------
elif pagina == "Estimación":
    st.title("⚡ Estimar calorías automáticamente")

    pendientes = df[df["calorías_estimadas"] == 0.0].copy()
    if pendientes.empty:
        st.info("No hay filas pendientes")
        st.stop()

    st.write(f"Filas pendientes: {len(pendientes)}")
    st.dataframe(pendientes[["Fecha","hora","comida","calorías_estimadas"]], use_container_width=True)

    csv_text = pendientes.rename(columns={
        "Fecha":"fecha","hora":"hora","comida":"descripcion","calorías_estimadas":"calorias"
    })[["fecha","hora","descripcion","calorias"]].to_csv(index=False)

    prompt = f"""
ROL: Eres un asistente nutricional especializado en estimación de alimentos consumidos en España.

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
Sin texto adicional. Solo el CSV.
"""

    if st.button("Ejecutar estimación"):
        response = model.generate_content(prompt)
        raw = re.sub(r"^```.*?\n|\n```$", "", response.text.strip(), flags=re.DOTALL)
        df_est = pd.read_csv(StringIO(raw))
        df_est.columns = ["Fecha","hora","comida","calorías_estimadas","carbohidratos_g","proteinas_g","sodio_nivel"]
        df_est["Fecha"] = pd.to_datetime(df_est["Fecha"]).dt.date
        df_est["carbohidratos_g"] = pd.to_numeric(df_est["carbohidratos_g"], errors="coerce")
        df_est["proteinas_g"] = pd.to_numeric(df_est["proteinas_g"], errors="coerce")
        keys = ["Fecha","hora","comida"]
        df = df.merge(
            df_est[keys + ["calorías_estimadas","carbohidratos_g","proteinas_g","sodio_nivel"]],
            on=keys, how="left", suffixes=("","_new")
        )
        df["calorías_estimadas"] = df["calorías_estimadas_new"].fillna(df["calorías_estimadas"])
        for col in ["carbohidratos_g","proteinas_g","sodio_nivel"]:
            df[col] = df[col+"_new"].combine_first(df[col])
        df = df.drop(columns=[c for c in df.columns if c.endswith("_new")])
        save_data(df, "Estimar calorías y macros")
        st.cache_data.clear()
        st.success("Estimación completada")
        st.rerun()

# ---------------- PÁGINA 5: MODELO DE PESO ----------------
elif pagina == "Modelo de peso":
    st.title("📊 Modelo explicativo del peso")

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

    # ---- Comidas diarias: total + alcohol ----
    _alc_kw = ["cerveza", "vino", "whiskey", "whisky", "gin", "ron", "vodka",
               "copa", "caña", "cubata", "cava", "chupito", "jager", "tequila",
               "licor", "vermut", "sidra"]
    _df = df.copy()
    _df["_alc"] = _df["comida"].str.lower().apply(lambda x: any(k in str(x) for k in _alc_kw))
    _df["_kcal_alc"] = _df["calorías_estimadas"].where(_df["_alc"], 0.0)
    _df["_carbs"] = pd.to_numeric(_df.get("carbohidratos_g", pd.Series(dtype=float)), errors="coerce")
    _df["_sodio_alto"] = (_df.get("sodio_nivel", pd.Series(dtype=str)) == "alto").astype(float)
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

    # ---- N por fase (diagnóstico de estabilidad) ----
    df_m = df_m.copy()
    df_m["fase"] = df_m.apply(
        lambda r: "Menstrual" if r["es_menstrual"] > 0.5
        else ("Lútea" if r["es_lutea"] > 0.5 else "Folicular"),
        axis=1
    )
    n_por_fase = df_m["fase"].value_counts().to_dict()

    # ---- Tabla de coeficientes ----
    st.subheader("¿Qué explica los cambios de peso?")
    coef_norm = w[1:]
    coef_orig = coef_norm / sigma
    df_coef = pd.DataFrame({
        "Variable": [FEAT[k] for k in feat_keys],
        "Efecto por unidad → g/día": np.round(coef_orig * 1000, 2),
        "Importancia relativa (%)":  np.round(np.abs(coef_norm) / np.abs(coef_norm).sum() * 100, 1),
    }).sort_values("Importancia relativa (%)", ascending=False).reset_index(drop=True)
    st.dataframe(df_coef, use_container_width=True)
    st.caption(
        "Para las variables de ciclo (fracción 0–1): el efecto es el máximo al pasar el período entero "
        "en esa fase. Con pocos datos por fase los coeficientes son inestables — ver N por fase abajo."
    )

    # ---- Efecto crudo por fase (sin modelo, solo descriptivo) ----
    st.subheader("Efecto crudo del ciclo — sin modelo")
    raw_fase = (df_m.groupby("fase")["delta_dia"]
                .agg(n="count", media_g=lambda x: x.mean() * 1000, std_g=lambda x: x.std() * 1000)
                .reset_index())
    raw_fase.columns = ["Fase", "N observaciones", "Δ Peso medio (g/día)", "Desv. típica (g/día)"]
    raw_fase["Δ Peso medio (g/día)"] = raw_fase["Δ Peso medio (g/día)"].round(1)
    raw_fase["Desv. típica (g/día)"] = raw_fase["Desv. típica (g/día)"].round(1)
    st.dataframe(raw_fase.sort_values("Fase"), use_container_width=True)
    st.caption(
        "Esta tabla no depende del modelo. Si la media de Δpeso en fase menstrual es negativa "
        "y en fase lútea positiva, el efecto del ciclo es real en tus datos. "
        "Si la N es <8, interpreta con mucha cautela."
    )

    # ---- Gráfica predicción vs real (último mes) ----
    st.subheader("Predicción vs realidad — último mes")
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
    fig_m.update_layout(yaxis_title="g/día", hovermode="x unified")
    st.plotly_chart(fig_m, use_container_width=True)

    # ---- Residuos por fase del ciclo ----
    st.subheader("Residuos por fase del ciclo")
    df_res = df_m.copy()
    df_res["residuo_g"] = (y - y_hat) * 1000
    fig_b = px.box(
        df_res, x="fase", y="residuo_g", color="fase",
        color_discrete_map={"Menstrual": "#e74c3c", "Folicular": "#2ecc71", "Lútea": "#f39c12"},
        labels={"residuo_g": "Residuo (g/día)", "fase": "Fase del ciclo"}
    )
    fig_b.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig_b, use_container_width=True)
    st.caption(
        "Residuos positivos = el peso subió más de lo predicho. "
        "Si los residuos de lútea son sistemáticamente positivos, el modelo está subestimando la retención de agua del ciclo."
    )
