import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# Configuración
st.set_page_config("Sueño", layout="centered")
st.title("🛌 Seguimiento de sueño")
ZONA = pytz.timezone("America/Bogota")
st_autorefresh(interval=1000, key="refresh_sueno")

# Conexión Mongo
client = MongoClient(st.secrets["mongo_uri"])
db = client["suenotest"]
col = db["registros"]

# Estado inicial
if "inicio_sueno" not in st.session_state:
    en_curso = col.find_one({"en_progreso": True})
    if en_curso:
        st.session_state.inicio_sueno = datetime.strptime(en_curso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
    else:
        st.session_state.inicio_sueno = None

# Bandera para activar cronómetro justo después de iniciar
if "mostrar_crono" not in st.session_state:
    st.session_state.mostrar_crono = False

# Cronómetro activo
if st.session_state.inicio_sueno:
    delta = datetime.now(ZONA) - st.session_state.inicio_sueno
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    st.markdown(f"**⏱️ Duración:** {h:02}:{m:02}:{s:02}")

    if st.button("✅ Finalizar sueño"):
        ahora = datetime.now(ZONA)
        duracion = str(timedelta(seconds=int((ahora - st.session_state.inicio_sueno).total_seconds())))
        col.update_one(
            {"en_progreso": True},
            {"$set": {
                "fin": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                "duracion": duracion,
                "en_progreso": False
            }}
        )
        st.session_state.inicio_sueno = None
        st.session_state.mostrar_crono = False
        st.success("🌞 Sueño finalizado")

# Botón de inicio
if not st.session_state.inicio_sueno:
    if st.button("😴 Iniciar sueño"):
        ahora = datetime.now(ZONA)
        col.insert_one({
            "inicio": ahora.strftime("%Y-%m-%d %H:%M:%S"),
            "fecha": ahora.strftime("%Y-%m-%d"),
            "en_progreso": True
        })
        st.session_state.inicio_sueno = ahora
        st.session_state.mostrar_crono = True
        st.success("😴 Sueño iniciado")

# Mostrar cronómetro justo después de iniciar (sin esperar otro clic)
if st.session_state.mostrar_crono and st.session_state.inicio_sueno:
    delta = datetime.now(ZONA) - st.session_state.inicio_sueno
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    st.markdown(f"**⏱️ Duración:** {h:02}:{m:02}:{s:02}")

# Historial
st.subheader("📊 Historial")
registros = list(col.find({"en_progreso": False}).sort("inicio", -1))
if registros:
    df = pd.DataFrame([{
        "Fecha": r["fecha"],
        "Inicio": r["inicio"],
        "Fin": r.get("fin", ""),
        "Duración": r.get("duracion", "")
    } for r in registros])
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("Sin registros finalizados.")
