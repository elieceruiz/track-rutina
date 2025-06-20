import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh

# ------------------------------------
# Configuration: App, Timezone, and DB
# ------------------------------------
st.set_page_config(page_title="Rutina Vital", layout="centered")
st_autorefresh(interval=1000, key="refresh")  # Refresh every second for real-time updates

ZONA = ZoneInfo("America/Bogota")

client = MongoClient(st.secrets["mongo_uri"])
db = client["rutina_vital"]
col_comidas = db["comidas"]
col_sueno = db["sueno"]
col_trabajo = db["trabajo"]
col_youtube = db["youtube_abstinencia"]

# -------------------------------
# Initialize session variables
# -------------------------------
if 'inicio' not in st.session_state:
    st.session_state.inicio = None
if 'tipo_comida' not in st.session_state:
    st.session_state.tipo_comida = None
if 'registro_comidas' not in st.session_state:
    st.session_state.registro_comidas = []
if 'cronometro_activo' not in st.session_state:
    st.session_state.cronometro_activo = False

# -------------------------------
# Main Title
# -------------------------------
st.title("🧠 Rutina Vital")
st.caption("Become aware of your time and habits")

# -------------------------------
# Section 1: Meal Tracking
# -------------------------------
st.header("🍽️ Meals with Timer")

if not st.session_state.cronometro_activo:
    tipo = st.selectbox("Select meal type to start timer:", ["--", "Breakfast", "Lunch", "Dinner", "Snack", "Break"])

    if tipo != "--":
        st.session_state.inicio = datetime.now(ZONA)
        st.session_state.tipo_comida = tipo
        st.session_state.cronometro_activo = True
        st.success(f"{tipo} started at {st.session_state.inicio.strftime('%H:%M:%S')}")

if st.session_state.cronometro_activo:
    elapsed = datetime.now(ZONA) - st.session_state.inicio
    mins, secs = divmod(elapsed.seconds, 60)
    hrs, mins = divmod(mins, 60)
    st.markdown(f"⏱️ **Elapsed Time:** {hrs:02d}:{mins:02d}:{secs:02d}")

    if st.button("Finish Meal"):
        fin = datetime.now(ZONA)
        duration = (fin - st.session_state.inicio).total_seconds() / 60

        evento = {
            "tipo": st.session_state.tipo_comida,
            "inicio": st.session_state.inicio.strftime('%H:%M:%S'),
            "fin": fin.strftime('%H:%M:%S'),
            "duracion_min": round(duration, 1),
            "fecha": fin.strftime('%Y-%m-%d')
        }

        st.session_state.registro_comidas.append(evento)
        col_comidas.insert_one(evento)

        st.success(f"{evento['tipo']} ended at {evento['fin']} - Duration: {evento['duracion_min']} minutes")

        st.session_state.inicio = None
        st.session_state.tipo_comida = None
        st.session_state.cronometro_activo = False

if st.session_state.registro_comidas:
    st.subheader("📋 Today's Meal History (session)")
    st.table(st.session_state.registro_comidas)

# -------------------------------
# Section 2: Sleep Tracking
# -------------------------------
st.header("🛌 Sleep Tracking")

acostarse_op = st.selectbox("Register bedtime?", ["--", "Yes"])
levantarse_op = st.selectbox("Register wake time?", ["--", "Yes"])

hora_acostarse = hora_levantarse = None
if acostarse_op == "Yes":
    hora_acostarse = st.time_input("What time did you go to bed?", key="hora_acostarse")
if levantarse_op == "Yes":
    hora_levantarse = st.time_input("What time did you wake up?", key="hora_levantarse")

if hora_acostarse and hora_levantarse and st.button("Save Sleep"):
    today = datetime.now(ZONA)
    t1 = datetime.combine(today.date(), hora_acostarse).replace(tzinfo=ZONA)
    t2 = datetime.combine(today.date(), hora_levantarse).replace(tzinfo=ZONA)
    if t2 < t1:
        t2 += timedelta(days=1)

    hours_slept = (t2 - t1).total_seconds() / 3600
    registro_sueno = {
        "acostarse": hora_acostarse.strftime('%H:%M'),
        "levantarse": hora_levantarse.strftime('%H:%M'),
        "duracion_horas": round(hours_slept, 2),
        "fecha": today.strftime('%Y-%m-%d')
    }
    col_sueno.insert_one(registro_sueno)

    color = "🟢" if hours_slept >= 6 else "🔴"
    st.success(f"{color} Slept {hours_slept:.1f} hours")

# -------------------------------
# Section 3: Work Arrival
# -------------------------------
st.header("🕘️ Work Arrival")

salida_op = st.selectbox("Register departure time?", ["--", "Yes"])
llegada_op = st.selectbox("Register arrival time?", ["--", "Yes"])

hora_salida = hora_llegada = None
if salida_op == "Yes":
    hora_salida = st.time_input("What time did you leave home?", key="salida")
if llegada_op == "Yes":
    hora_llegada = st.time_input("What time did you arrive at work?", key="llegada")

hora_esperada = st.time_input("What time are you expected at work?", value=datetime.strptime("07:00", "%H:%M").time(), key="esperada")

if hora_salida and hora_llegada and st.button("Register Arrival"):
    hoy = datetime.now(ZONA)
    t_salida = datetime.combine(hoy.date(), hora_salida).replace(tzinfo=ZONA)
    t_llegada = datetime.combine(hoy.date(), hora_llegada).replace(tzinfo=ZONA)
    t_esperada = datetime.combine(hoy.date(), hora_esperada).replace(tzinfo=ZONA)

    puntual = t_llegada <= t_esperada
    diferencia = (t_llegada - t_esperada).total_seconds() / 60
    registro_trabajo = {
        "salida": hora_salida.strftime('%H:%M'),
        "llegada": hora_llegada.strftime('%H:%M'),
        "esperada": hora_esperada.strftime('%H:%M'),
        "puntual": puntual,
        "diferencia_min": round(diferencia, 1),
        "fecha": hoy.strftime('%Y-%m-%d')
    }
    col_trabajo.insert_one(registro_trabajo)

    if puntual:
        st.success("🟢 On time!")
    else:
        st.error(f"🔴 Late by {abs(diferencia):.0f} minutes")

# -------------------------------
# Section 4: YouTube Abstinence
# -------------------------------
st.header("📵 YouTube Abstinence")

if st.checkbox("I wanted to enter YouTube but refrained"):
    evento = {
        "fecha": datetime.now(ZONA).strftime('%Y-%m-%d'),
        "hora": datetime.now(ZONA).strftime('%H:%M:%S'),
        "mensaje": "Abstinence registered"
    }
    col_youtube.insert_one(evento)
    st.success(f"✅ Registered: {evento['fecha']} at {evento['hora']}")

# -------------------------------
# Section 5: Historical Logs
# -------------------------------
st.header("📊 Historical Records")
tabs = st.tabs(["🍽️ Meals", "🛌 Sleep", "🕘️ Work", "📵 YouTube"])

with tabs[0]:
    comidas = list(col_comidas.find({}, {"_id": 0}))
    st.dataframe(comidas) if comidas else st.info("No records yet.")

with tabs[1]:
    suenos = list(col_sueno.find({}, {"_id": 0}))
    st.dataframe(suenos) if suenos else st.info("No records yet.")

with tabs[2]:
    trabajos = list(col_trabajo.find({}, {"_id": 0}))
    st.dataframe(trabajos) if trabajos else st.info("No records yet.")

with tabs[3]:
    abstinencias = list(col_youtube.find({}, {"_id": 0}))
    st.dataframe(abstinencias) if abstinencias else st.info("No records yet.")
