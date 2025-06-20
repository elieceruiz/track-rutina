import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
from zoneinfo import ZoneInfo

# -------------------------------
# Configurar zona horaria de Colombia
# -------------------------------
ZONA = ZoneInfo("America/Bogota")

# -------------------------------
# Conexión a MongoDB Atlas
# -------------------------------
client = MongoClient(st.secrets["mongo_uri"])
db = client["rutina_vital"]
col_comidas = db["comidas"]
col_sueno = db["sueno"]
col_trabajo = db["trabajo"]
col_youtube = db["youtube_abstinencia"]

# -------------------------------
# Inicializar variables de sesión
# -------------------------------
if 'inicio' not in st.session_state:
    st.session_state.inicio = None
if 'tipo_comida' not in st.session_state:
    st.session_state.tipo_comida = None
if 'registro_comidas' not in st.session_state:
    st.session_state.registro_comidas = []
if 'cronometro_activo' not in st.session_state:
    st.session_state.cronometro_activo = False
if 'registro_sueno' not in st.session_state:
    st.session_state.registro_sueno = {}
if 'registro_trabajo' not in st.session_state:
    st.session_state.registro_trabajo = {}

# -------------------------------
# Título principal
# -------------------------------
st.title("🧠 Rutina Vital")
st.caption("Hazte consciente de tu tiempo y hábitos")

# -------------------------------
# Sección 1: Registro de comidas
# -------------------------------
st.header("🍽️ Comidas con cronómetro")

if not st.session_state.cronometro_activo:
    tipo = st.selectbox("Selecciona tipo de comida para iniciar cronómetro:", ["--", "Desayuno", "Almuerzo", "Cena", "Snack", "Break"])
    
    if tipo != "--":
        st.session_state.inicio = datetime.now(ZONA)
        st.session_state.tipo_comida = tipo
        st.session_state.cronometro_activo = True
        st.success(f"{tipo} iniciado a las {st.session_state.inicio.strftime('%H:%M:%S')}")

if st.session_state.cronometro_activo:
    tiempo_transcurrido = datetime.now(ZONA) - st.session_state.inicio
    minutos, segundos = divmod(tiempo_transcurrido.seconds, 60)
    horas, minutos = divmod(minutos, 60)
    st.markdown(f"⏱️ **Tiempo transcurrido:** {horas:02d}:{minutos:02d}:{segundos:02d}")
    
    if st.button("Finalizar comida"):
        fin = datetime.now(ZONA)
        duracion = (fin - st.session_state.inicio).total_seconds() / 60

        evento = {
            "tipo": st.session_state.tipo_comida,
            "inicio": st.session_state.inicio.strftime('%H:%M:%S'),
            "fin": fin.strftime('%H:%M:%S'),
            "duracion_min": round(duracion, 1),
            "fecha": fin.strftime('%Y-%m-%d')
        }

        st.session_state.registro_comidas.append(evento)
        col_comidas.insert_one(evento)

        st.success(f"{evento['tipo']} finalizado a las {evento['fin']} - Duración: {evento['duracion_min']} minutos")

        st.session_state.inicio = None
        st.session_state.tipo_comida = None
        st.session_state.cronometro_activo = False

if st.session_state.registro_comidas:
    st.subheader("📋 Historial de comidas de hoy (sesión)")
    st.table(st.session_state.registro_comidas)

# -------------------------------
# Sección 2: Registro de sueño
# -------------------------------
st.header("😴 Registro de sueño")

hora_acostarse = st.time_input("¿A qué hora te acostaste?", key="hora_acostarse")
hora_levantarse = st.time_input("¿A qué hora te levantaste?", key="hora_levantarse")

if st.button("Guardar sueño"):
    hoy = datetime.now(ZONA)
    t1 = datetime.combine(hoy.date(), hora_acostarse).replace(tzinfo=ZONA)
    t2 = datetime.combine(hoy.date(), hora_levantarse).replace(tzinfo=ZONA)
    if t2 < t1:
        t2 += timedelta(days=1)

    horas_dormidas = (t2 - t1).total_seconds() / 3600
    st.session_state.registro_sueno = {
        "acostarse": hora_acostarse.strftime('%H:%M'),
        "levantarse": hora_levantarse.strftime('%H:%M'),
        "duracion_horas": round(horas_dormidas, 2),
        "fecha": hoy.strftime('%Y-%m-%d')
    }

    col_sueno.insert_one(st.session_state.registro_sueno)

    color = "🟢" if horas_dormidas >= 6 else "🔴"
    st.success(f"{color} Dormiste {horas_dormidas:.1f} horas")

if st.session_state.registro_sueno:
    st.subheader("📋 Sueño registrado (sesión)")
    st.json(st.session_state.registro_sueno)

# -------------------------------
# Sección 3: Puntualidad laboral
# -------------------------------
st.header("🕘 Llegada al trabajo")

hora_salida = st.time_input("¿A qué hora saliste de casa?", key="salida")
hora_llegada = st.time_input("¿A qué hora llegaste al trabajo?", key="llegada")
hora_esperada = st.time_input("¿A qué hora debes estar allá normalmente?", value=datetime.strptime("07:00", "%H:%M").time(), key="esperada")

if st.button("Registrar llegada"):
    hoy = datetime.now(ZONA)
    t_salida = datetime.combine(hoy.date(), hora_salida).replace(tzinfo=ZONA)
    t_llegada = datetime.combine(hoy.date(), hora_llegada).replace(tzinfo=ZONA)
    t_esperada = datetime.combine(hoy.date(), hora_esperada).replace(tzinfo=ZONA)

    puntual = t_llegada <= t_esperada
    diferencia = (t_llegada - t_esperada).total_seconds() / 60
    st.session_state.registro_trabajo = {
        "salida": hora_salida.strftime('%H:%M'),
        "llegada": hora_llegada.strftime('%H:%M'),
        "esperada": hora_esperada.strftime('%H:%M'),
        "puntual": puntual,
        "diferencia_min": round(diferencia, 1),
        "fecha": hoy.strftime('%Y-%m-%d')
    }

    col_trabajo.insert_one(st.session_state.registro_trabajo)

    if puntual:
        st.success("🟢 ¡Llegaste a tiempo!")
    else:
        st.error(f"🔴 Llegaste tarde por {abs(diferencia):.0f} minutos")

if st.session_state.registro_trabajo:
    st.subheader("📋 Registro de llegada (sesión)")
    st.json(st.session_state.registro_trabajo)

# -------------------------------
# Sección 4: Abstinencia de YouTube
# -------------------------------
st.header("📵 Abstinencia de YouTube")

if st.checkbox("Tuve ganas de entrar a YouTube y me abstuve"):
    evento = {
        "fecha": datetime.now(ZONA).strftime('%Y-%m-%d'),
        "hora": datetime.now(ZONA).strftime('%H:%M:%S'),
        "mensaje": "Abstinencia registrada"
    }
    col_youtube.insert_one(evento)
    st.success(f"✅ Registrado: {evento['fecha']} a las {evento['hora']}")

# -------------------------------
# Sección 5: Historial de registros desde MongoDB
# -------------------------------
st.header("📊 Historial de registros")
tabs = st.tabs(["🍽️ Comidas", "😴 Sueño", "🕘 Trabajo", "📵 YouTube"])

with tabs[0]:
    st.subheader("🍽️ Historial de comidas")
    comidas = list(col_comidas.find({}, {"_id": 0}))
    if comidas:
        st.dataframe(comidas)
    else:
        st.info("Sin registros aún.")

with tabs[1]:
    st.subheader("😴 Historial de sueño")
    suenos = list(col_sueno.find({}, {"_id": 0}))
    if suenos:
        st.dataframe(suenos)
    else:
        st.info("Sin registros aún.")

with tabs[2]:
    st.subheader("🕘 Historial de llegada al trabajo")
    trabajos = list(col_trabajo.find({}, {"_id": 0}))
    if trabajos:
        st.dataframe(trabajos)
    else:
        st.info("Sin registros aún.")

with tabs[3]:
    st.subheader("📵 Registro de abstinencia de YouTube")
    abstinencias = list(col_youtube.find({}, {"_id": 0}))
    if abstinencias:
        st.dataframe(abstinencias)
    else:
        st.info("Sin registros aún.")