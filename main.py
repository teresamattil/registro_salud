import streamlit as st
import pandas as pd
import requests
import base64
from datetime import date

st.set_page_config(page_title="Diario de comidas", layout="centered")

REPO = "teresamattil/registro_salud"
FILE = "comidas.csv"
API_URL = f"https://api.github.com/repos/{REPO}/contents/{FILE}"
RAW_URL = f"https://raw.githubusercontent.com/{REPO}/main/{FILE}"
TOKEN = st.secrets["GITHUB_TOKEN"]
HEADERS = {"Authorization": f"token {TOKEN}"}

@st.cache_data(ttl=60)
def load_data():
    return pd.read_csv(RAW_URL)

df = load_data()
df["fecha"] = pd.to_datetime(df["fecha"]).dt.date

st.title("🍽️ Diario de comidas")

dia = st.date_input("Día", date.today())
st.dataframe(df[df["fecha"] == dia], use_container_width=True)

st.divider()

with st.form("add_food"):
    f = st.date_input("Fecha", date.today())
    c = st.text_input("Comida")
    k = st.number_input("Calorías", min_value=0)
    submit = st.form_submit_button("Guardar")

if submit:
    r = requests.get(API_URL, headers=HEADERS).json()
    sha = r["sha"]

    df = pd.concat([df, pd.DataFrame([[f, c, k]], columns=df.columns)])
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
    st.success("Comida guardada")
    st.rerun()
st.markdown("---")
st.markdown("Hecho con ❤️ por Teresa")