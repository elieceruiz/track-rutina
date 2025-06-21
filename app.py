import streamlit as st
from datetime import datetime
from pymongo import MongoClient
from zoneinfo import ZoneInfo
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# Zona horaria
ZONA = ZoneInfo("America/Bogota")

# Conexión MongoDB
client = MongoClient(st.secrets["mongo_uri"])
db = client["rutina_vital"]
col_sueno = db["sueno"]

# Estado inicial
if "inicio_sueno" not in st.session_state:
    st.session_state.inicio_sueno = None
if "id_sueno_en_curso" not in st.session_state:
    st.session_state.id_sueno_en_curso = None

# Función para mostrar cronómetro
def mostrar_cronometro(inicio):
    delta = datetime.now(ZONA) - inicio
    h, rem = divmod(delta.seconds, 3600)
    m, s = divmod(rem, 60)
    st.markdown(f"**🛌 Duración del sueño:** {h:02}:{m:02}:{s:02}")

# Título
st.title("🛌 Registro de Sueño")

# Restaurar estado desde Mongo si hay un sueño en curso
en_curso = col_sueno.find_one({"en_progreso": True})
if en_curso:
    if not st.session_state.inicio_sueno:
        st.session_state.inicio_sueno = datetime.strptime(en_curso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
        st.session_state.id_sueno_en_curso = en_curso["_id"]

# Iniciar sueño
if not st.session_state.inicio_sueno:
    if st.button("Iniciar sueño"):
        ahora = datetime.now(ZONA)
        resultado = col_sueno.insert_one({
            "inicio": ahora.strftime("%Y-%m-%d %H:%M:%S"),
            "fecha": ahora.strftime("%Y-%m-%d"),
            "en_progreso": True
        })
        st.session_state.inicio_sueno = ahora
        st.session_state.id_sueno_en_curso = resultado.inserted_id
        st.success("😴 Cronómetro de sueño iniciado")

# Si hay sueño en curso
if st.session_state.inicio_sueno:
    st_autorefresh(interval=1000, key="refresh_sueno")
    mostrar_cronometro(st.session_state.inicio_sueno)
    
    if st.button("Finalizar sueño"):
        fin = datetime.now(ZONA)
        duracion = (fin - st.session_state.inicio_sueno).total_seconds() / 3600
        resultado = col_sueno.update_one(
            {"_id": st.session_state.id_sueno_en_curso, "en_progreso": True},
            {"$set": {
                "fin": fin.strftime("%Y-%m-%d %H:%M:%S"),
                "duracion_horas": round(duracion, 2),
                "en_progreso": False
            }}
        )
        if resultado.modified_count == 1:
            st.success("🌞 Sueño finalizado")
            st.session_state.inicio_sueno = None
            st.session_state.id_sueno_en_curso = None
        else:
            st.error("❌ No se pudo finalizar el sueño. Verifica si aún está en curso.")

# Historial
st.subheader("📊 Historial de sueño")
historial = list(col_sueno.find({"en_progreso": False}, {"_id": 0}).sort("inicio", -1))
if historial:
    st.dataframe(historial)
else:
    st.info("No hay registros finalizados.")
