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
    keys = [
        ("inicio_comida", "cronometro_comida"),
        ("inicio_sueno", "cronometro_sueno"),
        ("inicio_trabajo", "cronometro_trabajo"),
        ("tipo_comida", None)
    ]
    for inicio_key, cron_key in keys:
        if inicio_key not in st.session_state:
            st.session_state[inicio_key] = None
        if cron_key and cron_key not in st.session_state:
            st.session_state[cron_key] = False

init_session()

st.title("🧠 Rutina Vital")
st.caption("Hazte consciente de tu tiempo y hábitos")

secciones = st.tabs(["🍽️ Comidas", "🛌 Sueño", "🏢 Trabajo", "📵 YouTube"])

with secciones[0]:
    st.header("🍽️ Comidas con cronómetro")

    comida_en_progreso = col_comidas.find_one({"en_progreso": True})
    if comida_en_progreso and not st.session_state.cronometro_comida:
        st.session_state.tipo_comida = comida_en_progreso["tipo"]
        st.session_state.inicio_comida = datetime.strptime(comida_en_progreso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
        st.session_state.cronometro_comida = True

    if not st.session_state.cronometro_comida:
        tipo = st.selectbox("Selecciona tipo de comida para iniciar cronómetro:", ["--", "Desayuno", "Almuerzo", "Cena", "Snack", "Break"])
        if tipo != "--":
            inicio = datetime.now(ZONA)
            st.session_state.tipo_comida = tipo
            st.session_state.inicio_comida = inicio
            st.session_state.cronometro_comida = True
            col_comidas.insert_one({"tipo": tipo, "inicio": inicio.strftime('%Y-%m-%d %H:%M:%S'), "fecha": inicio.strftime('%Y-%m-%d'), "en_progreso": True})
            st.success(f"{tipo} iniciado a las {inicio.strftime('%H:%M:%S')}")

    if st.session_state.cronometro_comida:
        tiempo = datetime.now(ZONA) - st.session_state.inicio_comida
        h, m = divmod(tiempo.seconds, 3600)
        m, s = divmod(m, 60)
        st.markdown(f"🕰️ Tiempo transcurrido: **{h:02d}:{m:02d}:{s:02d}**")
        if st.button("Finalizar comida"):
            fin = datetime.now(ZONA)
            duracion = (fin - st.session_state.inicio_comida).total_seconds() / 60
            col_comidas.update_one({"en_progreso": True}, {"$set": {"fin": fin.strftime('%Y-%m-%d %H:%M:%S'), "duracion_min": round(duracion, 2), "en_progreso": False}})
            st.success(f"Comida finalizada - Duración: {duracion:.1f} minutos")
            st.session_state.cronometro_comida = False

    st.subheader("📊 Historial de comidas")
    datos = list(col_comidas.find({"en_progreso": False}, {"_id": 0}).sort("inicio", -1))
    st.dataframe(datos)

with secciones[1]:
    st.header("🛌 Registro de sueño")

    sueno_en_progreso = col_sueno.find_one({"en_progreso": True})
    if sueno_en_progreso and not st.session_state.cronometro_sueno:
        st.session_state.inicio_sueno = datetime.strptime(sueno_en_progreso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
        st.session_state.cronometro_sueno = True

    if not st.session_state.cronometro_sueno and st.button("Iniciar sueño"):
        inicio = datetime.now(ZONA)
        st.session_state.inicio_sueno = inicio
        st.session_state.cronometro_sueno = True
        col_sueno.insert_one({"inicio": inicio.strftime('%Y-%m-%d %H:%M:%S'), "fecha": inicio.strftime('%Y-%m-%d'), "en_progreso": True})
        st.success(f"Sueño iniciado a las {inicio.strftime('%H:%M:%S')}")

    if st.session_state.cronometro_sueno:
        tiempo = datetime.now(ZONA) - st.session_state.inicio_sueno
        h, m = divmod(tiempo.seconds, 3600)
        m, s = divmod(m, 60)
        st.markdown(f"⏳ Duración del sueño: **{h:02d}:{m:02d}:{s:02d}**")
        if st.button("Finalizar sueño"):
            fin = datetime.now(ZONA)
            duracion = (fin - st.session_state.inicio_sueno).total_seconds() / 3600
            col_sueno.update_one({"en_progreso": True}, {"$set": {"fin": fin.strftime('%Y-%m-%d %H:%M:%S'), "duracion_horas": round(duracion, 2), "en_progreso": False}})
            st.success(f"Sueño finalizado - Dormiste {duracion:.2f} horas")
            st.session_state.cronometro_sueno = False

    st.subheader("📊 Historial de sueño")
    datos = list(col_sueno.find({"en_progreso": False}, {"_id": 0}).sort("inicio", -1))
    st.dataframe(datos)

with secciones[2]:
    st.header("🏢 Registro de llegada al trabajo")

    trabajo_en_progreso = col_trabajo.find_one({"en_progreso": True})
    if trabajo_en_progreso and not st.session_state.cronometro_trabajo:
        st.session_state.inicio_trabajo = datetime.strptime(trabajo_en_progreso["salida"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
        st.session_state.cronometro_trabajo = True

    if not st.session_state.cronometro_trabajo and st.button("Registrar salida de casa"):
        salida = datetime.now(ZONA)
        st.session_state.inicio_trabajo = salida
        st.session_state.cronometro_trabajo = True
        col_trabajo.insert_one({"salida": salida.strftime('%Y-%m-%d %H:%M:%S'), "fecha": salida.strftime('%Y-%m-%d'), "en_progreso": True})
        st.success(f"Salida registrada a las {salida.strftime('%H:%M:%S')}")

    if st.session_state.cronometro_trabajo:
        tiempo = datetime.now(ZONA) - st.session_state.inicio_trabajo
        h, m = divmod(tiempo.seconds, 3600)
        m, s = divmod(m, 60)
        st.markdown(f"🛎 Tiempo desde salida: **{h:02d}:{m:02d}:{s:02d}**")
        if st.button("Registrar llegada al trabajo"):
            llegada = datetime.now(ZONA)
            duracion = (llegada - st.session_state.inicio_trabajo).total_seconds() / 60
            col_trabajo.update_one({"en_progreso": True}, {"$set": {"llegada": llegada.strftime('%Y-%m-%d %H:%M:%S'), "duracion_min": round(duracion, 2), "en_progreso": False}})
            st.success(f"Llegada registrada - Duración: {duracion:.1f} minutos")
            st.session_state.cronometro_trabajo = False

    st.subheader("📊 Historial de trabajo")
    datos = list(col_trabajo.find({"en_progreso": False}, {"_id": 0}).sort("salida", -1))
    st.dataframe(datos)

with secciones[3]:
    st.header("📵 Abstinencia de YouTube")

    if st.checkbox("Tuve ganas de entrar a YouTube y me abstuve"):
        if st.button("Registrar abstinencia"):
            ahora = datetime.now(ZONA)
            col_youtube.insert_one({"fecha": ahora.strftime('%Y-%m-%d'), "hora": ahora.strftime('%H:%M:%S'), "mensaje": "Abstinencia registrada"})
            st.success(f"Registrado: {ahora.strftime('%Y-%m-%d %H:%M:%S')}")

    st.subheader("📊 Historial de abstinencia")
    datos = list(col_youtube.find({}, {"_id": 0}).sort("fecha", -1))
    st.dataframe(datos)
