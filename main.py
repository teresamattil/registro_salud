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
        return pd.DataFrame(columns=["Fecha","hora","comida","ruta_foto","calorías_estimadas"])
    content = base64.b64decode(r["content"])
    return pd.read_csv(pd.io.common.BytesIO(content))

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

df = load_data()
df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date

# ---------------- MENU VISUAL ----------------

pagina = option_menu(
    menu_title=None,
    options=["Resumen diario", "Registro", "Peso & Calorías", "Estimación"],
    icons=["calendar-check", "calendar3", "speedometer2", "lightning-fill"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    key="menu_nav"
)

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
        r = st.text_input("Ruta foto")
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
            "ruta_foto": r,
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
                st.session_state["menu_nav"] = "Resumen diario"
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

    vista = st.radio("Vista", ["Diario", "Tendencia mensual"], horizontal=True)

    if vista == "Diario":
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_merged["Fecha"], y=df_merged["calorías_estimadas"],
            name="Calorías", yaxis="y1",
            line=dict(color="#115a8e"), mode="lines+markers"
        ))
        fig.add_trace(go.Scatter(
            x=df_merged["Fecha"], y=df_merged["peso_kg"],
            name="Peso (kg)", yaxis="y2",
            line=dict(color="#e74c3c"), mode="lines+markers"
        ))
        fig.add_hline(y=objetivo, line_dash="dash", line_color="orange", annotation_text="Objetivo kcal")
        fig.update_layout(
            yaxis=dict(title="Calorías"),
            yaxis2=dict(title="Peso (kg)", overlaying="y", side="right"),
            legend=dict(x=0.01, y=0.99),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        df_m = df_merged.copy()
        df_m["Fecha"] = pd.to_datetime(df_m["Fecha"])
        df_m["Mes"] = df_m["Fecha"].dt.to_period("M").astype(str)

        df_mes = (
            df_m.groupby("Mes", as_index=False)
            .agg(calorias_medias=("calorías_estimadas", "mean"), peso_medio=("peso_kg", "mean"))
            .dropna(subset=["peso_medio"])
        )

        x_idx = np.arange(len(df_mes))
        tendencia = np.poly1d(np.polyfit(x_idx, df_mes["peso_medio"], 1))(x_idx)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_mes["Mes"], y=df_mes["calorias_medias"],
            name="Calorías medias diarias", marker_color="#115a8e", yaxis="y1", opacity=0.7
        ))
        fig.add_trace(go.Scatter(
            x=df_mes["Mes"], y=df_mes["peso_medio"],
            name="Peso medio (kg)", yaxis="y2",
            line=dict(color="#e74c3c", width=2), mode="lines+markers"
        ))
        fig.add_trace(go.Scatter(
            x=df_mes["Mes"], y=tendencia,
            name="Tendencia peso", yaxis="y2",
            line=dict(color="#e74c3c", dash="dash", width=1.5), mode="lines"
        ))
        fig.update_layout(
            yaxis=dict(title="Calorías medias diarias"),
            yaxis2=dict(title="Peso (kg)", overlaying="y", side="right"),
            legend=dict(x=0.01, y=0.99),
            hovermode="x unified"
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
    st.dataframe(pendientes[["Fecha","hora","comida","ruta_foto","calorías_estimadas"]], use_container_width=True)
    
    csv_text = pendientes.rename(columns={
        "Fecha":"fecha",
        "hora":"hora",
        "comida":"descripcion",
        "calorías_estimadas":"calorias"
    })[["fecha","hora","descripcion","calorias"]].to_csv(index=False)

    prompt = f"""
ROL:
Eres un asistente nutricional especializado en estimación calórica de alimentos consumidos en registros diarios.

OBJETIVO:
Rellenar la última columna de un registro de comidas con una estimación realista de calorías por ítem, basándote en raciones habituales en España. Solo debes modificar los valores que estén a 0 o 0.0.

FORMATO DEL TEXTO DE ENTRADA:
{csv_text}

FORMATO DEL TEXTO DE SALIDA:
El mismo texto en formato CSV, respetando exactamente las columnas y el orden, pero sustituyendo el valor de calorías por la estimación correspondiente.
No añadas explicaciones ni texto adicional. Devuelve únicamente el bloque de código CSV.
"""

    if st.button("Ejecutar estimación"):
        response = model.generate_content(prompt)
        raw = re.sub(r"^```.*?\n|\n```$", "", response.text.strip(), flags=re.DOTALL)

        df_est = pd.read_csv(StringIO(raw))
        df_est.columns = ["Fecha","hora","comida","calorías_estimadas"]
        df_est["Fecha"] = pd.to_datetime(df_est["Fecha"]).dt.date

        keys = ["Fecha","hora","comida"]
        df = df.merge(
            df_est[keys + ["calorías_estimadas"]],
            on=keys,
            how="left",
            suffixes=("", "_new")
        )
        df["calorías_estimadas"] = df["calorías_estimadas_new"].fillna(df["calorías_estimadas"])
        df = df.drop(columns=["calorías_estimadas_new"])

        save_data(df, "Estimar calorías automáticamente")

        st.cache_data.clear()
        st.success("Estimación completada")
        st.rerun()
