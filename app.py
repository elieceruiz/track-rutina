import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
from zoneinfo import ZoneInfo
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
def init_session():
    for key in ["inicio_comida", "tipo_comida", "cronometro_comida", "inicio_sueno", "cronometro_sueno", "inicio_trabajo", "cronometro_trabajo"]:
        if key not in st.session_state:
            st.session_state[key] = None

init_session()

# App title
st.title("🧠 Rutina Vital")
st.caption("Hazte consciente de tu tiempo y hábitos")

# Tabs
secciones = st.tabs(["🍽️ Comidas", "🛌 Sueño", "🏢 Trabajo", "📵 YouTube"])

# (1) COMIDAS
with secciones[0]:
    st.header("🍽️ Comidas con cronómetro")

    comidas_en_progreso = list(col_comidas.find({"en_progreso": True}))
    comida_en_progreso = comidas_en_progreso[0] if comidas_en_progreso else None

    if comida_en_progreso and not st.session_state.cronometro_comida:
        st.session_state.tipo_comida = comida_en_progreso["tipo"]
        st.session_state.inicio_comida = datetime.strptime(comida_en_progreso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
        st.session_state.cronometro_comida = True

    if st.session_state.cronometro_comida:
        st_autorefresh(interval=1000, key="cronometro_comida")
        tiempo = datetime.now(ZONA) - st.session_state.inicio_comida
        st.markdown(f"**Tiempo transcurrido:** {tiempo}")
        if st.button("Finalizar comida"):
            fin = datetime.now(ZONA)
            duracion = (fin - st.session_state.inicio_comida).total_seconds() / 60
            col_comidas.update_one(
                {"en_progreso": True},
                {"$set": {"fin": fin.strftime("%Y-%m-%d %H:%M:%S"), "duracion_min": round(duracion, 2), "en_progreso": False}}
            )
            st.success(f"Comida finalizada. Duró {duracion:.2f} minutos")
            st.session_state.tipo_comida = None
            st.session_state.inicio_comida = None
            st.session_state.cronometro_comida = False
    else:
        tipo = st.selectbox("Tipo de comida:", ["--", "Desayuno", "Almuerzo", "Cena", "Snack", "Break"])
        if tipo != "--":
            ahora = datetime.now(ZONA)
            col_comidas.insert_one({"tipo": tipo, "inicio": ahora.strftime("%Y-%m-%d %H:%M:%S"), "fecha": ahora.strftime("%Y-%m-%d"), "en_progreso": True})
            st.session_state.tipo_comida = tipo
            st.session_state.inicio_comida = ahora
            st.session_state.cronometro_comida = True
            st.experimental_rerun()

# (2) SUEÑO
with secciones[1]:
    st.header("🛌 Registro de sueño")

    sueno_en_progreso = col_sueno.find_one({"en_progreso": True})
    if sueno_en_progreso and not st.session_state.cronometro_sueno:
        st.session_state.inicio_sueno = datetime.strptime(sueno_en_progreso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
        st.session_state.cronometro_sueno = True

    if st.session_state.cronometro_sueno:
        st_autorefresh(interval=1000, key="cronometro_sueno")
        tiempo = datetime.now(ZONA) - st.session_state.inicio_sueno
        st.markdown(f"**Duración del sueño:** {tiempo}")
        if st.button("Finalizar sueño"):
            fin = datetime.now(ZONA)
            duracion = (fin - st.session_state.inicio_sueno).total_seconds() / 3600
            col_sueno.update_one({"en_progreso": True}, {"$set": {"fin": fin.strftime("%Y-%m-%d %H:%M:%S"), "duracion_horas": round(duracion, 2), "en_progreso": False}})
            st.success(f"Dormiste {duracion:.2f} horas")
            st.session_state.inicio_sueno = None
            st.session_state.cronometro_sueno = False
    else:
        if st.button("Iniciar sueño"):
            ahora = datetime.now(ZONA)
            col_sueno.insert_one({"inicio": ahora.strftime("%Y-%m-%d %H:%M:%S"), "fecha": ahora.strftime("%Y-%m-%d"), "en_progreso": True})
            st.session_state.inicio_sueno = ahora
            st.session_state.cronometro_sueno = True
            st.experimental_rerun()

# (3) TRABAJO
with secciones[2]:
    st.header("🏢 Registro de llegada al trabajo")

    trabajo_en_progreso = col_trabajo.find_one({"en_progreso": True})
    if trabajo_en_progreso and not st.session_state.cronometro_trabajo:
        st.session_state.inicio_trabajo = datetime.strptime(trabajo_en_progreso["salida"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
        st.session_state.cronometro_trabajo = True

    if st.session_state.cronometro_trabajo:
        st_autorefresh(interval=1000, key="cronometro_trabajo")
        tiempo = datetime.now(ZONA) - st.session_state.inicio_trabajo
        st.markdown(f"**Tiempo desde salida:** {tiempo}")
        if st.button("Registrar llegada"):
            llegada = datetime.now(ZONA)
            minutos = (llegada - st.session_state.inicio_trabajo).total_seconds() / 60
            col_trabajo.update_one({"en_progreso": True}, {"$set": {"llegada": llegada.strftime("%Y-%m-%d %H:%M:%S"), "duracion_min": round(minutos, 2), "en_progreso": False}})
            st.success(f"Trayecto: {minutos:.1f} minutos")
            st.session_state.inicio_trabajo = None
            st.session_state.cronometro_trabajo = False
    else:
        if st.button("Registrar salida"):
            ahora = datetime.now(ZONA)
            col_trabajo.insert_one({"salida": ahora.strftime("%Y-%m-%d %H:%M:%S"), "fecha": ahora.strftime("%Y-%m-%d"), "en_progreso": True})
            st.session_state.inicio_trabajo = ahora
            st.session_state.cronometro_trabajo = True
            st.experimental_rerun()

# (4) YOUTUBE
with secciones[3]:
    st.header("📵 Abstinencia de YouTube")
    if st.button("Registrar abstinencia"):
        ahora = datetime.now(ZONA)
        col_youtube.insert_one({"fecha": ahora.strftime("%Y-%m-%d"), "hora": ahora.strftime("%H:%M:%S"), "mensaje": "Abstinencia registrada"})
        st.success("Registrado")

    st.subheader("Historial")
    data = list(col_youtube.find({}, {"_id": 0}).sort("fecha", -1))
    if data:
        st.dataframe(data)
    else:
        st.info("No hay registros.")
