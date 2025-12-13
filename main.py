import streamlit as st
import pandas as pd
import requests
import base64
from datetime import date, datetime

st.set_page_config(page_title="Diario de comidas", layout="centered")

REPO = "teresamattil/registro_salud"
FILE = "comidas.csv"
API_URL = f"https://api.github.com/repos/{REPO}/contents/{FILE}"
RAW_URL = f"https://raw.githubusercontent.com/{REPO}/main/{FILE}"
TOKEN = st.secrets["GITHUB_TOKEN"]
HEADERS = {"Authorization": f"token {TOKEN}"}

@st.cache_data(ttl=60)
def load_data():
    r = requests.get(API_URL, headers=HEADERS).json()
    content = base64.b64decode(r["content"])
    return pd.read_csv(pd.io.common.BytesIO(content))

df = load_data()
df["fecha"] = pd.to_datetime(df["fecha"]).dt.date

st.title("🍽️ Diario de comidas prueba")

dia = st.date_input("Día", date.today())
st.dataframe(df[df["fecha"] == dia], use_container_width=True)

st.divider()

with st.form("add_food"):
    f = st.date_input("Fecha", date.today())
    h = st.time_input("Hora", datetime.now().time())
    c = st.text_input("Comida")
    r = st.text_input("Ruta foto")
    k = st.number_input("Calorías estimadas", min_value=0)
    submit = st.form_submit_button("Guardar")

if submit:
    r_api = requests.get(API_URL, headers=HEADERS).json()
    sha = r_api["sha"]

    h_str = h.strftime("%H:%M")

    new_row = {
        "fecha": f,
        "hora": h_str,
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
    st.success("Comida guardada correctamente.")