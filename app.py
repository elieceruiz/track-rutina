import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import pytz
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# Configuración general
st.set_page_config(page_title="SueñoTrack", layout="centered")
st.title("🛌 Seguimiento de Sueño")
colombia = pytz.timezone("America/Bogota")
st_autorefresh(interval=1000, key="refresh_sueno")

# Conexión MongoDB
client = MongoClient(st.secrets["mongo_uri"])
db = client["sueno_tracker"]
coleccion = db["sueno"]

# Inicializar estado
if "inicio_sueno" not in st.session_state:
    doc = coleccion.find_one({"fin": {"$exists": False}}, sort=[("inicio", -1)])
    if doc:
        st.session_state.inicio_sueno = doc["inicio"].astimezone(colombia)
    else:
        st.session_state.inicio_sueno = None

# Mostrar cronómetro y botón de finalizar
if st.session_state.inicio_sueno:
    ahora = datetime.now(colombia)
    delta = ahora - st.session_state.inicio_sueno
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    st.markdown(f"**⏱️ Duración del sueño:** {h:02}:{m:02}:{s:02}")

    if st.button("✅ Finalizar sueño"):
        coleccion.update_one(
            {"inicio": st.session_state.inicio_sueno},
            {"$set": {
                "fin": ahora,
                "duracion_seg": int(delta.total_seconds())
            }}
        )
        st.success(f"🌞 Sueño finalizado: {ahora.strftime('%H:%M:%S')}")
        st.session_state.inicio_sueno = None

# Botón para iniciar
else:
    if st.button("😴 Iniciar sueño"):
        ahora = datetime.now(colombia)
        coleccion.insert_one({"inicio": ahora})
        st.session_state.inicio_sueno = ahora
        st.success(f"😴 Inicio registrado: {ahora.strftime('%H:%M:%S')}")

# Historial
st.subheader("📊 Historial")
registros = list(coleccion.find({"fin": {"$exists": True}}).sort("inicio", -1))

if registros:
    df = pd.DataFrame([{
        "Inicio": r["inicio"].astimezone(colombia).strftime("%Y-%m-%d %H:%M:%S"),
        "Fin": r["fin"].astimezone(colombia).strftime("%Y-%m-%d %H:%M:%S"),
        "Duración (min)": round(r["duracion_seg"] / 60, 1)
    } for r in registros])
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No hay registros todavía.")
