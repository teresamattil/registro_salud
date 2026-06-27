import streamlit as st
import pandas as pd
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

df = load_data()
df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date

# ---------------- MENU VISUAL ----------------

pagina = option_menu(
    menu_title=None,
    options=["Resumen diario", "Evolución", "Estimación"],
    icons=["calendar-check", "graph-up", "lightning-fill"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal"
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
elif pagina == "Evolución":
    st.title("📈 Evolución de calorías")

    df_daily = df.groupby("Fecha", as_index=False)["calorías_estimadas"].sum()

    vista = st.radio(
        "Vista",
        ["Último mes (diario)", "Rango personalizado", "Media mensual (anual)"],
        horizontal=True
    )

    if vista == "Último mes (diario)":
        ultimo_mes = date.today() - pd.Timedelta(days=30)
        df_plot = df_daily[df_daily["Fecha"] >= ultimo_mes].copy()

        dias = ["L", "M", "X", "J", "V", "S", "D"]
        df_plot["Etiqueta"] = (
            df_plot["Fecha"].apply(lambda d: f"{dias[d.weekday()]} {d.day}")
        )

        fig = px.line(
            df_plot,
            x="Etiqueta",
            y="calorías_estimadas",
            markers=True
        )
        fig.add_hline(y=objetivo, line_dash="dash", line_color="orange")
        st.plotly_chart(fig, use_container_width=True)


    elif vista == "Rango personalizado":
        col1, col2 = st.columns(2)
        with col1:
            inicio = st.date_input("Fecha inicio", df_daily["Fecha"].min())
        with col2:
            fin = st.date_input("Fecha fin", df_daily["Fecha"].max())

        df_plot = df_daily[(df_daily["Fecha"]>=inicio)&(df_daily["Fecha"]<=fin)].copy()
        df_plot["Hasta_objetivo"] = df_plot["calorías_estimadas"].clip(upper=objetivo)
        df_plot["Exceso"] = (df_plot["calorías_estimadas"]-objetivo).clip(lower=0)

        fig = go.Figure()
        fig.add_bar(x=df_plot["Fecha"], y=df_plot["Hasta_objetivo"], marker_color="#115a8e", name="Hasta objetivo")
        fig.add_bar(x=df_plot["Fecha"], y=df_plot["Exceso"], marker_color="#d93725", name="Exceso")
        fig.update_layout(barmode="stack")
        st.plotly_chart(fig, use_container_width=True)

    else:
        df_m = df.copy()
        df_m["Fecha"] = pd.to_datetime(df_m["Fecha"])

        # Suma diaria
        df_diario = (
            df_m.groupby("Fecha", as_index=False)["calorías_estimadas"].sum()
        )

        # Año, mes y quincena
        df_diario["Año"] = df_diario["Fecha"].dt.year
        df_diario["Mes"] = df_diario["Fecha"].dt.month
        df_diario["Quincena"] = df_diario["Fecha"].dt.day.apply(
            lambda d: 1 if d <= 15 else 2
        )

        # Media quincenal de calorías diarias
        df_avg = (
            df_diario
            .groupby(["Año", "Mes", "Quincena"], as_index=False)["calorías_estimadas"]
            .mean()
        )

        df_avg["Periodo"] = (
            df_avg["Año"].astype(str)
            + "-"
            + df_avg["Mes"].astype(str)
            + " Q"
            + df_avg["Quincena"].astype(str)
        )

        fig = px.line(df_avg, x="Periodo", y="calorías_estimadas", markers=True)
        fig.add_hline(y=objetivo, line_dash="dash", line_color="orange")
        st.plotly_chart(fig, use_container_width=True)



# ---------------- PÁGINA 3 ----------------
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
