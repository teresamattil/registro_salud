import streamlit as st
import pandas as pd
import requests
import base64
from datetime import date, datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Diario de comidas", layout="centered")

REPO = "teresamattil/registro_salud"
FILE = "comidas.csv"
API_URL = f"https://api.github.com/repos/{REPO}/contents/{FILE}"
TOKEN = st.secrets["GITHUB_TOKEN"]
HEADERS = {"Authorization": f"token {TOKEN}"}
objetivo = 2000

@st.cache_data(ttl=60)
def load_data():
    r = requests.get(API_URL, headers=HEADERS).json()
    if "content" not in r:
        return pd.DataFrame(
            columns=["Fecha", "hora", "comida", "ruta_foto", "calorías_estimadas"]
        )
    content = base64.b64decode(r["content"])
    return pd.read_csv(pd.io.common.BytesIO(content))

df = load_data()
df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date

# ---------------- NAVEGADOR ----------------
pagina = st.radio(
    "Navegación",
    ["📅 Resumen diario", "📈 Evolución"],
    horizontal=True
)

# ================= PÁGINA 1 =================
if pagina == "📅 Resumen diario":
    st.title("🍽️ Diario de comidas")

    if "dia_seleccionado" not in st.session_state:
        st.session_state.dia_seleccionado = date.today()

    dia = st.date_input(
        "Día",
        st.session_state.dia_seleccionado,
        key="dia_selector"
    )
    st.session_state.dia_seleccionado = dia

    cols_resumen = ["Fecha", "hora", "comida", "calorías_estimadas"]
    st.dataframe(
        df[df["Fecha"] == dia][cols_resumen],
        use_container_width=True
    )

    if "mostrar_grafico" not in st.session_state:
        st.session_state.mostrar_grafico = False

    if st.button("📊 Ver calorías del día"):
        st.session_state.mostrar_grafico = not st.session_state.mostrar_grafico

    if st.session_state.mostrar_grafico:

        consumidas = df[df["Fecha"] == dia]["calorías_estimadas"].sum()
        restantes = max(objetivo - consumidas, 0)

        fig = go.Figure(
            data=[go.Pie(
                values=[consumidas, restantes],
                labels=["Consumidas", "Restantes"],
                hole=0.7,
                textinfo="none"
            )]
        )

        fig.add_annotation(
            text=f"{int(consumidas)} kcal",
            x=0.5,
            y=0.5,
            font_size=24,
            showarrow=False
        )

        fig.update_layout(
            title=f"Calorías del día ({consumidas} / {objetivo})",
            margin=dict(t=50, b=0, l=0, r=0)
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    with st.form("add_food"):
        f = st.date_input("Fecha", st.session_state.dia_seleccionado)
        h = st.time_input("Hora", datetime.now().time())
        c = st.text_input("Comida")
        r = st.text_input("Ruta foto")
        k = st.number_input("Calorías estimadas", min_value=0)
        submit = st.form_submit_button("Guardar")

    if submit:
        r_api = requests.get(API_URL, headers=HEADERS).json()
        sha = r_api["sha"]

        new_row = {
            "Fecha": f,
            "hora": h.strftime("%H:%M"),
            "comida": c,
            "ruta_foto": r,
            "calorías_estimadas": k
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        csv = df.to_csv(index=False)
        content = base64.b64encode(csv.encode()).decode()

        requests.put(
            API_URL,
            headers=HEADERS,
            json={
                "message": "Añadir comida",
                "content": content,
                "sha": sha
            }
        )

        st.cache_data.clear()
        st.rerun()

# ================= PÁGINA 2 =================
if pagina == "📈 Evolución":
    st.title("Evolución de calorías")

    df_daily = (
        df.groupby("Fecha", as_index=False)["calorías_estimadas"]
        .sum()
        .sort_values("Fecha")
    )

    vista = st.radio(
        "Vista",
        ["Último mes (diario)", "Rango personalizado", "Media mensual (anual)"],
        horizontal=True
    )

    if vista == "Último mes (diario)":
        ultimo_mes = date.today().replace(day=1)
        df_plot = df_daily[df_daily["Fecha"] >= ultimo_mes]

        fig = px.line(
            df_plot,
            x="Fecha",
            y="calorías_estimadas",
            markers=True,
            title="Calorías diarias (último mes)"
        )

        fig.add_hline(
            y=objetivo,
            line_dash="dash",
            line_color="orange",
            annotation_text="Objetivo",
            annotation_position="top left"
        )

        st.plotly_chart(fig, use_container_width=True)

    elif vista == "Rango personalizado":
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=df_plot["Fecha"],
            y=df_plot["Hasta_objetivo"],
            name="Hasta objetivo",
            marker_color="#115a8e"
        ))

        fig.add_trace(go.Bar(
            x=df_plot["Fecha"],
            y=df_plot["Exceso"],
            name="Exceso",
            marker_color="#d93725"
        ))

        fig.update_layout(
            barmode="stack",
            title="Calorías diarias (rango personalizado)",
        )

        st.plotly_chart(fig, use_container_width=True)



    else:
        df_monthly = df.copy()
        df_monthly["Año"] = pd.to_datetime(df_monthly["Fecha"]).dt.year
        df_monthly["Mes"] = pd.to_datetime(df_monthly["Fecha"]).dt.month

        df_avg = (
            df_monthly.groupby(["Año", "Mes"])["calorías_estimadas"]
            .mean()
            .reset_index()
        )

        df_avg["Periodo"] = df_avg["Año"].astype(str) + "-" + df_avg["Mes"].astype(str)

        fig = px.line(
            df_avg,
            x="Periodo",
            y="calorías_estimadas",
            markers=True,
            title="Media diaria mensual (visión anual)"
        )

        fig.add_hline(
            y=objetivo,
            line_dash="dash",
            line_color="orange",
            annotation_text="Objetivo",
            annotation_position="top left"
        )

        st.plotly_chart(fig, use_container_width=True)
