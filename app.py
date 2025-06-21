import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import pytz
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# Config
st.set_page_config("SueñoTrack", layout="centered")
st.title("🛌 Seguimiento de Sueño")
ZONA = pytz.timezone("America/Bogota")

# Forzar actualización cada segundo solo si hay cronómetro activo
if "inicio_sueno" in st.session_state and st.session_state.inicio_sueno:
    st_autorefresh(interval=1000, key="refresh_sueno")

# Mongo
client = MongoClient(st.secrets["mongo_uri"])
db = client["sueno_tracker"]
col = db["sueno"]

# Inicializar sesión
if "inicio_sueno" not in st.session_state:
    doc = col.find_one({"fin": {"$exists": False}}, sort=[("inicio", -1)])
    st.session_state.inicio_sueno = doc["inicio"].astimezone(ZONA) if doc else None

# Funciones
def mostrar_crono(inicio):
    ahora = datetime.now(ZONA)
    delta = ahora - inicio
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    st.markdown(f"**🕰️ Tiempo durmiendo:** {h:02}:{m:02}:{s:02}")
    return ahora, delta

# Interfaz principal
if st.session_state.inicio_sueno:
    ahora, delta = mostrar_crono(st.session_state.inicio_sueno)
    if st.button("✅ Finalizar sueño"):
        col.update_one(
            {"inicio": st.session_state.inicio_sueno.replace(tzinfo=None)},
            {"$set": {
                "fin": ahora,
                "duracion_seg": int(delta.total_seconds())
            }}
        )
        st.session_state.inicio_sueno = None
        st.success("🌞 Sueño finalizado")

else:
    if st.button("😴 Iniciar sueño"):
        ahora = datetime.now(ZONA)
        col.insert_one({"inicio": ahora})
        st.session_state.inicio_sueno = ahora
        st.success("⏱️ Cronómetro iniciado")

# Historial
st.subheader("📊 Historial")
registros = list(col.find({"fin": {"$exists": True}}).sort("inicio", -1))

if registros:
    df = pd.DataFrame([{
        "Inicio": r["inicio"].astimezone(ZONA).strftime("%Y-%m-%d %H:%M:%S"),
        "Fin": r["fin"].astimezone(ZONA).strftime("%Y-%m-%d %H:%M:%S"),
        "Duración (min)": round(r["duracion_seg"] / 60, 1)
    } for r in registros])
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No hay registros aún.")
