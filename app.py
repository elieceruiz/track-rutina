import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
from zoneinfo import ZoneInfo

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
    for key in ["inicio_comida", "tipo_comida", "cronometro_comida",
                "inicio_sueno", "cronometro_sueno",
                "inicio_trabajo", "cronometro_trabajo"]:
        if key not in st.session_state:
            st.session_state[key] = None

init_session()

# App title
st.title("🧠 Rutina Vital")
st.caption("Hazte consciente de tu tiempo y hábitos")

# Tabs
secciones = st.tabs(["🍽️ Comidas", "🛌 Sueño", "🏢 Trabajo", "📵 YouTube"])

# 1. COMIDAS
with secciones[0]:
    st.header("🍽️ Comidas con cronómetro")

    comida_en_progreso = col_comidas.find_one({"en_progreso": True})
    if comida_en_progreso and not st.session_state.cronometro_comida:
        st.session_state.tipo_comida = comida_en_progreso["tipo"]
        st.session_state.inicio_comida = datetime.strptime(comida_en_progreso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
        st.session_state.cronometro_comida = True

    if not st.session_state.cronometro_comida:
        tipo = st.selectbox("Selecciona tipo de comida para iniciar:", ["--", "Desayuno", "Almuerzo", "Cena", "Snack", "Break"])
        if tipo != "--":
            inicio = datetime.now(ZONA)
            st.session_state.inicio_comida = inicio
            st.session_state.tipo_comida = tipo
            st.session_state.cronometro_comida = True
            col_comidas.insert_one({"tipo": tipo, "inicio": inicio.strftime('%Y-%m-%d %H:%M:%S'), "fecha": inicio.strftime('%Y-%m-%d'), "en_progreso": True})
            st.toast("⏱️ Cronómetro de comida iniciado")

    if st.session_state.cronometro_comida:
        tiempo = datetime.now(ZONA) - st.session_state.inicio_comida
        h, rem = divmod(tiempo.seconds, 3600)
        m, s = divmod(rem, 60)
        st.markdown(f"**🕰️ Tiempo transcurrido:** {h:02}:{m:02}:{s:02}")

        if st.button("Finalizar comida"):
            fin = datetime.now(ZONA)
            duracion = (fin - st.session_state.inicio_comida).total_seconds() / 60
            col_comidas.update_one({"en_progreso": True}, {"$set": {"fin": fin.strftime('%Y-%m-%d %H:%M:%S'), "duracion_min": round(duracion, 2), "en_progreso": False}})
            st.toast(f"✅ {st.session_state.tipo_comida} finalizado")
            st.session_state.tipo_comida = None
            st.session_state.inicio_comida = None
            st.session_state.cronometro_comida = None

    st.subheader("📊 Historial de comidas")
    df = list(col_comidas.find({"en_progreso": False}, {"_id": 0}).sort("inicio", -1))
    st.dataframe(df) if df else st.info("No hay registros finalizados.")

# 2. SUEÑO
with secciones[1]:
    st.header("🛌 Registro de sueño")

    sueno_en_progreso = col_sueno.find_one({"en_progreso": True})
    if sueno_en_progreso and not st.session_state.cronometro_sueno:
        st.session_state.inicio_sueno = datetime.strptime(sueno_en_progreso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
        st.session_state.cronometro_sueno = True

    if not st.session_state.cronometro_sueno:
        if st.button("Iniciar sueño"):
            inicio = datetime.now(ZONA)
            st.session_state.inicio_sueno = inicio
            st.session_state.cronometro_sueno = True
            col_sueno.insert_one({"inicio": inicio.strftime('%Y-%m-%d %H:%M:%S'), "fecha": inicio.strftime('%Y-%m-%d'), "en_progreso": True})
            st.toast("🌙 Registro de sueño iniciado")

    if st.session_state.cronometro_sueno:
        delta = datetime.now(ZONA) - st.session_state.inicio_sueno
        h, rem = divmod(delta.seconds, 3600)
        m, s = divmod(rem, 60)
        st.markdown(f"**⏳ Duración actual del sueño:** {h:02}:{m:02}:{s:02}")

        if st.button("Finalizar sueño"):
            fin = datetime.now(ZONA)
            horas = (fin - st.session_state.inicio_sueno).total_seconds() / 3600
            col_sueno.update_one({"en_progreso": True}, {"$set": {"fin": fin.strftime('%Y-%m-%d %H:%M:%S'), "duracion_horas": round(horas, 2), "en_progreso": False}})
            st.toast("🛏️ Sueño finalizado")
            st.session_state.inicio_sueno = None
            st.session_state.cronometro_sueno = None

    st.subheader("📊 Historial de sueño")
    df = list(col_sueno.find({"en_progreso": False}, {"_id": 0}).sort("inicio", -1))
    st.dataframe(df) if df else st.info("No hay registros finalizados.")

# 3. TRABAJO
with secciones[2]:
    st.header("🏢 Registro de llegada al trabajo")

    trabajo_en_progreso = col_trabajo.find_one({"en_progreso": True})
    if trabajo_en_progreso and not st.session_state.cronometro_trabajo:
        st.session_state.inicio_trabajo = datetime.strptime(trabajo_en_progreso["salida"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
        st.session_state.cronometro_trabajo = True

    if not st.session_state.cronometro_trabajo:
        if st.button("Registrar salida de casa"):
            salida = datetime.now(ZONA)
            st.session_state.inicio_trabajo = salida
            st.session_state.cronometro_trabajo = True
            col_trabajo.insert_one({"salida": salida.strftime('%Y-%m-%d %H:%M:%S'), "fecha": salida.strftime('%Y-%m-%d'), "en_progreso": True})
            st.toast("🚶‍♂️ Salida registrada")

    if st.session_state.cronometro_trabajo:
        delta = datetime.now(ZONA) - st.session_state.inicio_trabajo
        h, rem = divmod(delta.seconds, 3600)
        m, s = divmod(rem, 60)
        st.markdown(f"**⏱️ Tiempo desde salida:** {h:02}:{m:02}:{s:02}")

        if st.button("Registrar llegada al trabajo"):
            llegada = datetime.now(ZONA)
            minutos = (llegada - st.session_state.inicio_trabajo).total_seconds() / 60
            col_trabajo.update_one({"en_progreso": True}, {"$set": {"llegada": llegada.strftime('%Y-%m-%d %H:%M:%S'), "duracion_min": round(minutos, 2), "en_progreso": False}})
            st.toast("🏁 Llegada registrada")
            st.session_state.inicio_trabajo = None
            st.session_state.cronometro_trabajo = None

    st.subheader("📊 Historial de trabajo")
    df = list(col_trabajo.find({"en_progreso": False}, {"_id": 0}).sort("salida", -1))
    st.dataframe(df) if df else st.info("No hay registros finalizados.")

# 4. YOUTUBE ABSTINENCIA
with secciones[3]:
    st.header("📵 Abstinencia de YouTube")
    if st.checkbox("Tuve ganas de entrar a YouTube y me abstuve"):
        if st.button("Registrar abstinencia"):
            evento = {
                "fecha": datetime.now(ZONA).strftime('%Y-%m-%d'),
                "hora": datetime.now(ZONA).strftime('%H:%M:%S'),
                "mensaje": "Abstinencia registrada"
            }
            col_youtube.insert_one(evento)
            st.success(f"✅ Registrado: {evento['fecha']} a las {evento['hora']}")

    st.subheader("📊 Historial de abstinencia")
    eventos = list(col_youtube.find({}, {"_id": 0}).sort("fecha", -1))
    st.dataframe(eventos) if eventos else st.info("No hay registros aún.")
