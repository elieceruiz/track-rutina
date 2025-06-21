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
    for key in ["inicio_comida", "tipo_comida", "cronometro_comida", "acostarse_en_curso", "trabajo_en_curso"]:
        if key not in st.session_state:
            st.session_state[key] = None

init_session()

# App title
st.title("🧠 Rutina Vital")
st.caption("Hazte consciente de tu tiempo y hábitos")

# Section 1 - Meal tracker
st.header("🍽️ Comidas con cronómetro")

comida_en_progreso = col_comidas.find_one({"en_progreso": True})
if comida_en_progreso and not st.session_state.cronometro_comida:
    st.session_state.tipo_comida = comida_en_progreso["tipo"]
    st.session_state.inicio_comida = datetime.strptime(comida_en_progreso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
    st.session_state.cronometro_comida = True

if st.session_state.cronometro_comida:
    st_autorefresh(interval=1000, key="cronometro_comida_refresh")

if not st.session_state.cronometro_comida:
    tipo = st.selectbox("Selecciona tipo de comida para iniciar cronómetro:", ["--", "Desayuno", "Almuerzo", "Cena", "Snack", "Break"])
    if tipo != "--":
        with st.spinner("Iniciando cronómetro..."):
            inicio = datetime.now(ZONA)
            st.session_state.inicio_comida = inicio
            st.session_state.tipo_comida = tipo
            st.session_state.cronometro_comida = True
            col_comidas.insert_one({"tipo": tipo, "inicio": inicio.strftime('%Y-%m-%d %H:%M:%S'), "fecha": inicio.strftime('%Y-%m-%d'), "en_progreso": True})
        st.success(f"{tipo} iniciado a las {inicio.strftime('%H:%M:%S')}")

if st.session_state.cronometro_comida:
    tiempo_transcurrido = datetime.now(ZONA) - st.session_state.inicio_comida
    minutos, segundos = divmod(tiempo_transcurrido.seconds, 60)
    horas, minutos = divmod(minutos, 60)
    st.markdown(f"🕰️ Tiempo transcurrido: **{horas:02d}:{minutos:02d}:{segundos:02d}**")

    if st.button("Finalizar comida"):
        fin = datetime.now(ZONA)
        duracion = (fin - st.session_state.inicio_comida).total_seconds() / 60
        resultado = col_comidas.update_one(
            {"en_progreso": True, "tipo": st.session_state.tipo_comida},
            {"$set": {
                "fin": fin.strftime('%Y-%m-%d %H:%M:%S'),
                "duracion_min": round(duracion, 2),
                "en_progreso": False
            }}
        )
        if resultado.modified_count > 0:
            st.success(f"{st.session_state.tipo_comida} finalizado a las {fin.strftime('%H:%M:%S')} - Duración: {duracion:.1f} minutos")
        st.session_state.inicio_comida = None
        st.session_state.tipo_comida = None
        st.session_state.cronometro_comida = False

# Section 2 - Sleep tracking
st.header("🛌 Registro de sueño")

sueno_en_progreso = col_sueno.find_one({"en_progreso": True})
if sueno_en_progreso and not st.session_state.acostarse_en_curso:
    st.session_state.acostarse_en_curso = datetime.strptime(sueno_en_progreso["acostarse"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)

if st.session_state.acostarse_en_curso:
    st_autorefresh(interval=1000, key="cronometro_sueno_refresh")

if not st.session_state.acostarse_en_curso:
    if st.button("Registrar hora de acostarse"):
        ahora = datetime.now(ZONA)
        col_sueno.insert_one({"acostarse": ahora.strftime('%Y-%m-%d %H:%M:%S'), "fecha": ahora.strftime('%Y-%m-%d'), "en_progreso": True})
        st.session_state.acostarse_en_curso = ahora
        st.success(f"Hora de acostarse registrada: {ahora.strftime('%H:%M:%S')}")

if st.session_state.acostarse_en_curso:
    tiempo_sueno = datetime.now(ZONA) - st.session_state.acostarse_en_curso
    horas, rem = divmod(tiempo_sueno.seconds, 3600)
    minutos, segundos = divmod(rem, 60)
    st.markdown(f"💤 Dormido durante: **{horas:02d}:{minutos:02d}:{segundos:02d}**")

    if st.button("Registrar hora de levantarse"):
        ahora = datetime.now(ZONA)
        t1 = st.session_state.acostarse_en_curso
        t2 = ahora if ahora > t1 else ahora + timedelta(days=1)
        horas_dormidas = (t2 - t1).total_seconds() / 3600
        resultado = col_sueno.update_one({"en_progreso": True}, {"$set": {"levantarse": ahora.strftime('%Y-%m-%d %H:%M:%S'), "duracion_horas": round(horas_dormidas, 2), "en_progreso": False}})
        if resultado.modified_count > 0:
            color = "🟢" if horas_dormidas >= 6 else "🔴"
            st.success(f"{color} Dormiste {horas_dormidas:.1f} horas")
        st.session_state.acostarse_en_curso = None

# Section 3 - Work punctuality
st.header("🕘️ Llegada al trabajo")

trabajo_en_progreso = col_trabajo.find_one({"en_progreso": True})
if trabajo_en_progreso and not st.session_state.trabajo_en_curso:
    st.session_state.trabajo_en_curso = datetime.strptime(trabajo_en_progreso["salida"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)

if st.session_state.trabajo_en_curso:
    st_autorefresh(interval=1000, key="cronometro_trabajo_refresh")

if not st.session_state.trabajo_en_curso:
    if st.button("Registrar hora de salida de casa"):
        ahora = datetime.now(ZONA)
        col_trabajo.insert_one({
            "salida": ahora.strftime('%Y-%m-%d %H:%M:%S'),
            "fecha": ahora.strftime('%Y-%m-%d'),
            "en_progreso": True
        })
        st.session_state.trabajo_en_curso = ahora
        st.success(f"Hora de salida registrada: {ahora.strftime('%H:%M:%S')}")

if st.session_state.trabajo_en_curso:
    tiempo_trabajo = datetime.now(ZONA) - st.session_state.trabajo_en_curso
    horas, rem = divmod(tiempo_trabajo.seconds, 3600)
    minutos, segundos = divmod(rem, 60)
    st.markdown(f"🚶‍♂️ Tiempo desde salida: **{horas:02d}:{minutos:02d}:{segundos:02d}**")

    hora_esperada = st.time_input("¿A qué hora debes estar allá normalmente?", value=datetime.strptime("07:00", "%H:%M").time(), key="esperada")
    if st.button("Registrar hora de llegada al trabajo"):
        llegada = datetime.now(ZONA)
        salida = st.session_state.trabajo_en_curso
        t_esperada = datetime.combine(llegada.date(), hora_esperada).replace(tzinfo=ZONA)
        puntual = llegada <= t_esperada
        diferencia = (llegada - t_esperada).total_seconds() / 60
        resultado = col_trabajo.update_one(
            {"en_progreso": True},
            {"$set": {
                "llegada": llegada.strftime('%Y-%m-%d %H:%M:%S'),
                "esperada": t_esperada.strftime('%H:%M'),
                "puntual": puntual,
                "diferencia_min": round(diferencia, 1),
                "en_progreso": False
            }}
        )
        if resultado.modified_count > 0:
            if puntual:
                st.success("🟢 ¡Llegaste a tiempo!")
            else:
                st.error(f"🔴 Llegaste tarde por {abs(diferencia):.0f} minutos")
        st.session_state.trabajo_en_curso = None

# Section 4 - YouTube Abstinence
st.header("📵 Abstinencia de YouTube")

abstinencia = st.checkbox("Tuve ganas de entrar a YouTube y me abstuve")
if abstinencia and st.button("Registrar abstinencia"):
    evento = {"fecha": datetime.now(ZONA).strftime('%Y-%m-%d'), "hora": datetime.now(ZONA).strftime('%H:%M:%S'), "mensaje": "Abstinencia registrada"}
    col_youtube.insert_one(evento)
    st.success(f"✅ Registrado: {evento['fecha']} a las {evento['hora']}")

# Section 5 - Records history
st.header("📊 Historial de registros")
tabs = st.tabs(["🍽️ Meals", "🛌 Sleep", "🕘️ Work", "📵 YouTube"])

with tabs[0]:
    comidas = list(col_comidas.find({}, {"_id": 0}))
    if comidas:
        st.dataframe(comidas)
    else:
        st.info("No hay registros aún.")

with tabs[1]:
    suenos = list(col_sueno.find({}, {"_id": 0}))
    if suenos:
        st.dataframe(suenos)
    else:
        st.info("No hay registros aún.")

with tabs[2]:
    trabajos = list(col_trabajo.find({}, {"_id": 0}))
    if trabajos:
        st.dataframe(trabajos)
    else:
        st.info("No hay registros aún.")

with tabs[3]:
    abstinencias = list(col_youtube.find({}, {"_id": 0}))
    if abstinencias:
        st.dataframe(abstinencias)
    else:
        st.info("No hay registros aún.")
