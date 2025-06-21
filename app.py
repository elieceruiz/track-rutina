import streamlit as st
from datetime import datetime
from pymongo import MongoClient
from zoneinfo import ZoneInfo
import pandas as pd
from streamlit_autorefresh import st_autorefresh

ZONA = ZoneInfo("America/Bogota")

# MongoDB connection
client = MongoClient(st.secrets["mongo_uri"])
db = client["rutina_vital"]
col_comidas = db["comidas"]
col_sueno = db["sueno"]
col_trabajo = db["trabajo"]
col_youtube = db["youtube_abstinencia"]

# Session state initialization
def init_state():
    claves = [
        "inicio_comida", "tipo_comida",
        "inicio_sueno",
        "inicio_trabajo"
    ]
    for clave in claves:
        if clave not in st.session_state:
            st.session_state[clave] = None

init_state()

# Cronómetro dinámico
def mostrar_cronometro(inicio, label="⏱️ Tiempo transcurrido"):
    if inicio:
        delta = datetime.now(ZONA) - inicio
        h, rem = divmod(delta.seconds, 3600)
        m, s = divmod(rem, 60)
        st.markdown(f"**{label}:** {h:02}:{m:02}:{s:02}")

# App title
st.title("🧠 Rutina Vital")
st.caption("Hazte consciente de tu tiempo y hábitos")

# Tabs
tabs = st.tabs(["🍽️ Comidas", "🛌 Sueño", "🏢 Trabajo", "📵 YouTube"])

# 🍽️ COMIDAS
with tabs[0]:
    st.header("🍽️ Comidas con cronómetro")

    en_curso = col_comidas.find_one({"en_progreso": True})
    if en_curso and not st.session_state.inicio_comida:
        st.session_state.inicio_comida = datetime.strptime(en_curso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
        st.session_state.tipo_comida = en_curso["tipo"]

    if not st.session_state.inicio_comida:
        tipo = st.selectbox("Selecciona tipo de comida", ["--", "Desayuno", "Almuerzo", "Cena", "Snack"])
        if tipo != "--":
            ahora = datetime.now(ZONA)
            col_comidas.insert_one({
                "tipo": tipo,
                "inicio": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                "fecha": ahora.strftime("%Y-%m-%d"),
                "en_progreso": True
            })
            st.session_state.inicio_comida = ahora
            st.session_state.tipo_comida = tipo
            st.success("⏱️ Cronómetro iniciado")

    if st.session_state.inicio_comida:
        st_autorefresh(interval=1000, key="refresh_comida")
        mostrar_cronometro(st.session_state.inicio_comida, "🕰️ Tiempo comiendo")
        if st.button("Finalizar comida"):
            fin = datetime.now(ZONA)
            duracion = (fin - st.session_state.inicio_comida).total_seconds() / 60
            col_comidas.update_one(
                {"en_progreso": True},
                {"$set": {
                    "fin": fin.strftime("%Y-%m-%d %H:%M:%S"),
                    "duracion_min": round(duracion, 2),
                    "en_progreso": False
                }}
            )
            st.success(f"✅ {st.session_state.tipo_comida} finalizado")
            st.session_state.inicio_comida = None
            st.session_state.tipo_comida = None

    st.subheader("📊 Historial")
    historial = list(col_comidas.find({"en_progreso": False}, {"_id": 0}).sort("inicio", -1))
    if historial:
        st.dataframe(historial)
    else:
        st.info("No hay registros finalizados.")

# 🛌 SUEÑO
with tabs[1]:
    st.header("🛌 Registro de sueño")

    en_curso = col_sueno.find_one({"en_progreso": True})
    if en_curso and not st.session_state.inicio_sueno:
        st.session_state.inicio_sueno = datetime.strptime(en_curso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)

    if not st.session_state.inicio_sueno:
        if st.button("Iniciar sueño"):
            ahora = datetime.now(ZONA)
            col_sueno.insert_one({
                "inicio": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                "fecha": ahora.strftime("%Y-%m-%d"),
                "en_progreso": True
            })
            st.session_state.inicio_sueno = ahora
            st.success("😴 Cronómetro de sueño iniciado")

    if st.session_state.inicio_sueno:
        st_autorefresh(interval=1000, key="refresh_sueno")
        mostrar_cronometro(st.session_state.inicio_sueno, "🛌 Duración del sueño")
        if st.button("Finalizar sueño"):
            fin = datetime.now(ZONA)
            duracion = (fin - st.session_state.inicio_sueno).total_seconds() / 3600
            col_sueno.update_one(
                {"en_progreso": True},
                {"$set": {
                    "fin": fin.strftime("%Y-%m-%d %H:%M:%S"),
                    "duracion_horas": round(duracion, 2),
                    "en_progreso": False
                }}
            )
            st.success("🌞 Sueño finalizado")
            st.session_state.inicio_sueno = None

    st.subheader("📊 Historial")
    historial = list(col_sueno.find({"en_progreso": False}, {"_id": 0}).sort("inicio", -1))
    if historial:
        st.dataframe(historial)
    else:
        st.info("No hay registros finalizados.")

# 🏢 TRABAJO
with tabs[2]:
    st.header("🏢 Registro de llegada al trabajo")

    en_curso = col_trabajo.find_one({"en_progreso": True})
    if en_curso and not st.session_state.inicio_trabajo:
        st.session_state.inicio_trabajo = datetime.strptime(en_curso["salida"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)

    if not st.session_state.inicio_trabajo:
        if st.button("Registrar salida de casa"):
            ahora = datetime.now(ZONA)
            col_trabajo.insert_one({
                "salida": ahora.strftime("%Y-%m-%d %H:%M:%S"),
                "fecha": ahora.strftime("%Y-%m-%d"),
                "en_progreso": True
            })
            st.session_state.inicio_trabajo = ahora
            st.success("🏃‍♂️ Salida registrada")

    if st.session_state.inicio_trabajo:
        st_autorefresh(interval=1000, key="refresh_trabajo")
        mostrar_cronometro(st.session_state.inicio_trabajo, "🏁 Tiempo desde salida")
        if st.button("Registrar llegada al trabajo"):
            fin = datetime.now(ZONA)
            minutos = (fin - st.session_state.inicio_trabajo).total_seconds() / 60
            col_trabajo.update_one(
                {"en_progreso": True},
                {"$set": {
                    "llegada": fin.strftime("%Y-%m-%d %H:%M:%S"),
                    "duracion_min": round(minutos, 2),
                    "en_progreso": False
                }}
            )
            st.success("✅ Llegada registrada")
            st.session_state.inicio_trabajo = None

    st.subheader("📊 Historial")
    historial = list(col_trabajo.find({"en_progreso": False}, {"_id": 0}).sort("salida", -1))
    if historial:
        st.dataframe(historial)
    else:
        st.info("No hay registros finalizados.")

# 📵 YouTube
with tabs[3]:
    st.header("📵 Abstinencia de YouTube")
    if st.button("Registrar abstinencia"):
        ahora = datetime.now(ZONA)
        evento = {
            "fecha": ahora.strftime("%Y-%m-%d"),
            "hora": ahora.strftime("%H:%M:%S"),
            "mensaje": "Abstinencia registrada"
        }
        col_youtube.insert_one(evento)
        st.success(f"✅ Registrado: {evento['fecha']} a las {evento['hora']}")

    st.subheader("📊 Historial")
    eventos = list(col_youtube.find({}, {"_id": 0}).sort("fecha", -1))
    if eventos:
        st.dataframe(eventos)
    else:
        st.info("No hay registros aún.")
