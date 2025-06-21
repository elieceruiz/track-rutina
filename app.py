import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
import pytz
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# Configuración
st.set_page_config(page_title="Seguimiento de Sueño", layout="centered")
ZONA = pytz.timezone("America/Bogota")
st_autorefresh(interval=1000, key="refresh")

# Conexión Mongo
client = MongoClient(st.secrets["mongo_uri"])
db = client["seguimiento_sueno"]
col = db["sueno"]

# Estado inicial
if "inicio_sueno" not in st.session_state:
    st.session_state.inicio_sueno = None
if "trigger" not in st.session_state:
    st.session_state.trigger = False

# Si hay en curso, restaurar
if not st.session_state.inicio_sueno:
    en_curso = col.find_one({"en_progreso": True})
    if en_curso:
        dt = datetime.strptime(en_curso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
        st.session_state.inicio_sueno = dt

# Función para cronómetro
def mostrar_cronometro(inicio):
    delta = datetime.now(ZONA) - inicio
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    st.markdown(f"**🕒 Duración del sueño:** {h:02}:{m:02}:{s:02}")

# UI principal
st.title("🛌 Seguimiento de sueño")

# Cronómetro activo
if st.session_state.inicio_sueno:
    mostrar_cronometro(st.session_state.inicio_sueno)

    if st.button("🌞 Finalizar sueño"):
        fin = datetime.now(ZONA)
        duracion_td = fin - st.session_state.inicio_sueno
        duracion_str = str(timedelta(seconds=int(duracion_td.total_seconds())))

        col.update_one(
            {"en_progreso": True},
            {"$set": {
                "fin": fin.strftime("%Y-%m-%d %H:%M:%S"),
                "duracion_str": duracion_str,
                "en_progreso": False
            }}
        )

        st.session_state.inicio_sueno = None
        st.session_state.trigger = True
        st.success("✅ Sueño finalizado")

# Botón para iniciar nuevo
elif not st.session_state.inicio_sueno:
    if st.button("😴 Iniciar sueño"):
        ahora = datetime.now(ZONA)
        col.insert_one({
            "inicio": ahora.strftime("%Y-%m-%d %H:%M:%S"),
            "fecha": ahora.strftime("%Y-%m-%d"),
            "en_progreso": True
        })
        st.session_state.inicio_sueno = ahora
        st.success("🕒 Cronómetro iniciado")

# Mostrar historial
st.subheader("📊 Historial de sueño")
if st.session_state.trigger or not st.session_state.inicio_sueno:
    historial = list(col.find({"en_progreso": False}).sort("inicio", -1))
    if historial:
        for h in historial:
            h["Duración"] = h.get("duracion_str", "—")
            h["Inicio"] = h.get("inicio", "")
            h["Fin"] = h.get("fin", "")
        df = pd.DataFrame(historial)[["fecha", "Inicio", "Fin", "Duración"]]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No hay registros finalizados.")
