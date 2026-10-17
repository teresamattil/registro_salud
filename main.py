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
                     ("carbohidratos_g", pd.NA), ("proteinas_g", pd.NA), ("sodio_nivel", pd.NA)]:
    if col not in df.columns:
        df[col] = default
df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
df["calorías_estimadas"] = pd.to_numeric(df["calorías_estimadas"], errors="coerce").fillna(0)
df["momento"] = df["momento"].fillna("Comida")
rutinas = load_routines()

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
    options=["Hoy", "Pega tu semana", "Registro", "Evolución", "Modelo"],
    icons=["sun", "calendar-week", "list-ul", "graph-up", "cpu"],