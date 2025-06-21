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
    for key in [
        "inicio_comida", "tipo_comida", "cronometro_comida",
        "inicio_sueno", "cronometro_sueno",
        "inicio_trabajo", "cronometro_trabajo"
    ]:
        if key not in st.session_state:
            st.session_state[key] = None

init_session()

# App title
st.title("🧠 Rutina Vital")
st.caption("Hazte consciente de tu tiempo y hábitos")

# Tabs
secciones = st.tabs(["🍽️ Comidas", "🛌 Sueño", "🏢 Trabajo", "📵 YouTube"])

# --- Sección COMIDAS ---
with secciones[0]:
    st.header("🍽️ Comidas con cronómetro")

    comida_en_progreso = col_comidas.find_one({"en_progreso": True})
    if comida_en_progreso and not st.session_state.cronometro_comida:
        st.session_state.tipo_comida = comida_en_progreso["tipo"]
        st.session_state.inicio_comida = datetime.strptime(comida_en_progreso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
        st.session_state.cronometro_comida = True

    if st.session_state.cronometro_comida:
        st_autorefresh(interval=1000, key="cronometro_comida_refresh")
        tiempo_transcurrido = datetime.now(ZONA) - st.session_state.inicio_comida
        minutos, segundos = divmod(tiempo_transcurrido.seconds, 60)
        horas, minutos = divmod(minutos, 60)
        st.markdown(f"🕰️ Tiempo transcurrido: **{horas:02d}:{minutos:02d}:{segundos:02d}**")

        if st.button("Finalizar comida"):
            fin = datetime.now(ZONA)
            duracion = (fin - st.session_state.inicio_comida).total_seconds() / 60
            col_comidas.update_one(
                {"en_progreso": True},
                {"$set": {
                    "fin": fin.strftime('%Y-%m-%d %H:%M:%S'),
                    "duracion_min": round(duracion, 2),
                    "en_progreso": False
                }}
            )
            st.success(f"{st.session_state.tipo_comida} finalizado a las {fin.strftime('%H:%M:%S')} - Duración: {duracion:.1f} minutos")
            st.session_state.inicio_comida = None
            st.session_state.tipo_comida = None
            st.session_state.cronometro_comida = None

    else:
        tipo = st.selectbox("Selecciona tipo de comida para iniciar cronómetro:", ["--", "Desayuno", "Almuerzo", "Cena", "Snack", "Break"])
        if tipo != "--" and st.button("Iniciar comida"):
            inicio = datetime.now(ZONA)
            col_comidas.insert_one({"tipo": tipo, "inicio": inicio.strftime('%Y-%m-%d %H:%M:%S'), "fecha": inicio.strftime('%Y-%m-%d'), "en_progreso": True})
            st.session_state.tipo_comida = tipo
            st.session_state.inicio_comida = inicio
            st.session_state.cronometro_comida = True
            st.experimental_rerun()

    st.subheader("📊 Historial de comidas")
    registros = list(col_comidas.find({"en_progreso": False}, {"_id": 0}).sort("inicio", -1))
    st.dataframe(registros if registros else [])

# --- Sección SUEÑO ---
with secciones[1]:
    st.header("🛌 Registro de sueño")

    sueno_en_progreso = col_sueno.find_one({"en_progreso": True})
    if sueno_en_progreso and not st.session_state.cronometro_sueno:
        st.session_state.inicio_sueno = datetime.strptime(sueno_en_progreso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
        st.session_state.cronometro_sueno = True

    if st.session_state.cronometro_sueno:
        st_autorefresh(interval=1000, key="cronometro_sueno_refresh")
        tiempo = datetime.now(ZONA) - st.session_state.inicio_sueno
        h, rem = divmod(tiempo.seconds, 3600)
        m, s = divmod(rem, 60)
        st.markdown(f"⏳ Duración del sueño: **{h:02d}:{m:02d}:{s:02d}**")

        if st.button("Finalizar sueño"):
            fin = datetime.now(ZONA)
            duracion = (fin - st.session_state.inicio_sueno).total_seconds() / 3600
            col_sueno.update_one(
                {"en_progreso": True},
                {"$set": {
                    "fin": fin.strftime('%Y-%m-%d %H:%M:%S'),
                    "duracion_horas": round(duracion, 2),
                    "en_progreso": False
                }}
            )
            st.success(f"🔚 Finalizado a las {fin.strftime('%H:%M:%S')} - Dormiste {duracion:.2f} horas")
            st.session_state.inicio_sueno = None
            st.session_state.cronometro_sueno = None

    else:
        if st.button("Iniciar sueño"):
            inicio = datetime.now(ZONA)
            col_sueno.insert_one({"inicio": inicio.strftime('%Y-%m-%d %H:%M:%S'), "fecha": inicio.strftime('%Y-%m-%d'), "en_progreso": True})
            st.session_state.inicio_sueno = inicio
            st.session_state.cronometro_sueno = True
            st.experimental_rerun()

    st.subheader("📊 Historial de sueño")
    suenos = list(col_sueno.find({"en_progreso": False}, {"_id": 0}).sort("inicio", -1))
    st.dataframe(suenos if suenos else [])

# --- Sección TRABAJO ---
with secciones[2]:
    st.header("🏢 Registro de llegada al trabajo")

    trabajo_en_progreso = col_trabajo.find_one({"en_progreso": True})
    if trabajo_en_progreso and not st.session_state.cronometro_trabajo:
        st.session_state.inicio_trabajo = datetime.strptime(trabajo_en_progreso["salida"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
        st.session_state.cronometro_trabajo = True

    if st.session_state.cronometro_trabajo:
        st_autorefresh(interval=1000, key="cronometro_trabajo_refresh")
        tiempo = datetime.now(ZONA) - st.session_state.inicio_trabajo
        h, rem = divmod(tiempo.seconds, 3600)
        m, s = divmod(rem, 60)
        st.markdown(f"🕘 Tiempo desde salida: **{h:02d}:{m:02d}:{s:02d}**")

        if st.button("Registrar llegada"):
            llegada = datetime.now(ZONA)
            duracion = (llegada - st.session_state.inicio_trabajo).total_seconds() / 60
            col_trabajo.update_one(
                {"en_progreso": True},
                {"$set": {
                    "llegada": llegada.strftime('%Y-%m-%d %H:%M:%S'),
                    "duracion_min": round(duracion, 2),
                    "en_progreso": False
                }}
            )
            st.success(f"🏁 Llegada registrada a las {llegada.strftime('%H:%M:%S')} - Duración: {duracion:.1f} minutos")
            st.session_state.inicio_trabajo = None
            st.session_state.cronometro_trabajo = None

    else:
        if st.button("Registrar salida de casa"):
            salida = datetime.now(ZONA)
            col_trabajo.insert_one({"salida": salida.strftime('%Y-%m-%d %H:%M:%S'), "fecha": salida.strftime('%Y-%m-%d'), "en_progreso": True})
            st.session_state.inicio_trabajo = salida
            st.session_state.cronometro_trabajo = True
            st.experimental_rerun()

    st.subheader("📊 Historial de trabajo")
    trabajos = list(col_trabajo.find({"en_progreso": False}, {"_id": 0}).sort("salida", -1))
    st.dataframe(trabajos if trabajos else [])

# --- Sección YouTube ---
with secciones[3]:
    st.header("📵 Abstinencia de YouTube")

    if st.checkbox("Tuve ganas de entrar a YouTube y me abstuve"):
        if st.button("Registrar abstinencia"):
            ahora = datetime.now(ZONA)
            col_youtube.insert_one({
                "fecha": ahora.strftime('%Y-%m-%d'),
                "hora": ahora.strftime('%H:%M:%S'),
                "mensaje": "Abstinencia registrada"
            })
            st.success(f"✅ Registrado: {ahora.strftime('%Y-%m-%d')} a las {ahora.strftime('%H:%M:%S')}")

    st.subheader("📊 Historial de abstinencia")
    abstinencias = list(col_youtube.find({}, {"_id": 0}).sort("fecha", -1))
    st.dataframe(abstinencias if abstinencias else [])
