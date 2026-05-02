import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import time
from bson import ObjectId

# === CONFIGURACIÓN GENERAL ===
st.set_page_config("Contención", layout="centered")
st.title("📊 Contención")

# Zona horaria
tz = pytz.timezone("America/Bogota")

# Conexión a MongoDB
MONGO_URI = st.secrets["mongo_uri"]
client = MongoClient(MONGO_URI)
db = client["rutina_vital"]
coleccion = db["eventos"]

# === DELETE VIA LINK (ESTÉTICO) ===
params = st.query_params
if "delete" in params:
    try:
        coleccion.delete_one({"_id": ObjectId(params["delete"])})
        st.query_params.clear()
        st.rerun()
    except:
        st.warning("Error al borrar registro")

# Actividades disponibles
actividades_disponibles = [
    "Sueño", "Comidas", "Puntualidad", "Coding", "Ducha", "Leer", "Abstinencia", "Pagos"
]

# Selector principal
actividad = st.selectbox("Selecciona la actividad:", actividades_disponibles)

# Mapear nombres para Mongo
if actividad == "Comidas":
    tipo_mongo = "comida"
elif actividad == "Puntualidad":
    tipo_mongo = "puntualidad"
elif actividad == "Abstinencia":
    tipo_mongo = "abstinencia"
elif actividad == "Pagos":
    tipo_mongo = "pago"
else:
    tipo_mongo = actividad.lower()

# Mostrar si hay evento en curso
en_curso_actual = coleccion.find_one({"tipo": tipo_mongo, "en_curso": True})
if en_curso_actual:
    hora_ini = en_curso_actual["inicio"].astimezone(tz).strftime('%H:%M:%S')
    descripcion = en_curso_actual.get("subtipo", actividad).capitalize()
    st.warning(f"🔄 Tienes un **{descripcion}** en curso desde las {hora_ini}.")

# Variables base
evento = None
subtipo = None
hora_esperada = None

# === BLOQUE 1: Actividades básicas ===
if actividad in ["Sueño", "Comidas", "Coding", "Ducha", "Leer"]:
    if actividad == "Comidas":
        subtipo_opciones = ["Desayuno", "Almuerzo", "Cena", "Snack"]
        evento = coleccion.find_one({"tipo": "comida", "en_curso": True})
        if evento:
            subtipo = evento.get("subtipo", "desconocido").capitalize()
        else:
            subtipo = st.radio("Tipo de comida:", subtipo_opciones)
    else:
        evento = coleccion.find_one({"tipo": tipo_mongo, "en_curso": True})

    if evento:
        hora_inicio = evento["inicio"].astimezone(tz)
        segundos_transcurridos = int((datetime.now(tz) - hora_inicio).total_seconds())
        nombre_activa = actividad if actividad != "Comidas" else subtipo

        st.success(f"{nombre_activa} iniciado a las {hora_inicio.strftime('%H:%M:%S')}")
        cronometro = st.empty()
        stop_button = st.button("⏹️ Finalizar")

        for i in range(segundos_transcurridos, segundos_transcurridos + 100000):
            if stop_button:
                coleccion.update_one(
                    {"_id": evento["_id"]},
                    {"$set": {"fin": datetime.now(tz), "en_curso": False}}
                )
                st.success("✅ Registro finalizado.")
                st.rerun()

            duracion = str(timedelta(seconds=i))
            cronometro.markdown(f"### 🕒 Duración: {duracion}")
            time.sleep(1)

    else:
        if st.button("🟢 Iniciar"):
            nuevo_evento = {"tipo": tipo_mongo, "inicio": datetime.now(tz), "en_curso": True}
            if subtipo:
                nuevo_evento["subtipo"] = subtipo.lower()
            coleccion.insert_one(nuevo_evento)
            st.rerun()

# === BLOQUE 2: PUNTUALIDAD ===
elif actividad == "Puntualidad":
    evento = coleccion.find_one({"tipo": "puntualidad", "en_curso": True})

    if evento:
        hora_inicio = evento["inicio"].astimezone(tz)
        segundos_transcurridos = int((datetime.now(tz) - hora_inicio).total_seconds())
        tipo = evento.get("subtipo", "compromiso")
        hora_esperada = evento.get("hora_esperada", "00:00")

        st.success(f"{tipo.capitalize()} — desplazamiento iniciado a las {hora_inicio.strftime('%H:%M:%S')}")
        st.info(f"Debías llegar a las **{hora_esperada}**")

        cronometro = st.empty()
        stop_button = st.button("⏹️ Finalizar llegada")

        for i in range(segundos_transcurridos, segundos_transcurridos + 100000):
            if stop_button:
                ahora = datetime.now(tz)
                llegada_real = ahora.time()
                hora_obj = datetime.strptime(hora_esperada, "%H:%M").time()

                diferencia = (
                    datetime.combine(datetime.today(), llegada_real)
                    - datetime.combine(datetime.today(), hora_obj)
                ).total_seconds()

                diferencia_min = round(diferencia / 60)
                punctuality = "temprano" if diferencia <= 0 else "tarde"

                coleccion.update_one(
                    {"_id": evento["_id"]},
                    {"$set": {
                        "fin": ahora,
                        "en_curso": False,
                        "puntualidad": punctuality,
                        "diferencia_min": diferencia_min
                    }}
                )

                st.success("✅ Llegada registrada.")
                st.rerun()

            cronometro.markdown(f"### 🚶 Duración del desplazamiento: {str(timedelta(seconds=i))}")
            time.sleep(1)

    else:
        tipo_compromiso = st.radio("¿A dónde te diriges?", ["Clase", "Trabajo", "Cita médica", "Cita odontológica", "Otro"])
        hora_esperada = st.time_input("¿A qué hora deberías llegar?")

        if st.button("🟢 Iniciar desplazamiento"):
            ahora = datetime.now(tz)

            coleccion.insert_one({
                "tipo": "puntualidad",
                "subtipo": tipo_compromiso.lower(),
                "hora_esperada": hora_esperada.strftime("%H:%M"),
                "inicio": ahora,
                "en_curso": True
            })

            st.rerun()

# === BLOQUE 3: ABSTINENCIA ===
elif actividad == "Abstinencia":
    opciones = [
        "putas Medellín / putas Bello", "LinkedIn", "YouTube", "Apple TV+",
        "Domino's", "Uber", "Rapicredit", "MONET", "MAGIS"
    ]

    evento = coleccion.find_one({"tipo": "abstinencia", "en_curso": True})

    if evento:
        impulso = evento.get("subtipo", "impulso")
        hora_inicio = evento["inicio"].astimezone(tz)
        segundos_transcurridos = int((datetime.now(tz) - hora_inicio).total_seconds())

        st.success(f"🧠 Resistencia activa contra: {impulso}")

        cronometro = st.empty()
        stop_button = st.button("⏹️ Finalizar contención")

        for i in range(segundos_transcurridos, segundos_transcurridos + 100000):
            if stop_button:
                coleccion.update_one(
                    {"_id": evento["_id"]},
                    {"$set": {"fin": datetime.now(tz), "en_curso": False}}
                )

                st.success("✅ Contención registrada.")
                st.rerun()

            cronometro.markdown(f"### ⏱️ Tiempo resistido: {str(timedelta(seconds=i))}")
            time.sleep(1)

    else:
        impulso = st.radio("¿Cuál impulso estás resistiendo?", opciones)

        if st.button("🟢 Registrar impulso"):
            coleccion.insert_one({
                "tipo": "abstinencia",
                "subtipo": impulso,
                "inicio": datetime.now(tz),
                "en_curso": True
            })

            st.rerun()

# === BLOQUE 4: PAGOS ===
elif actividad == "Pagos":
    evento = coleccion.find_one({"tipo": "pago", "en_curso": True})

    if evento:
        descripcion = evento.get("subtipo", "pago")
        monto = evento.get("monto", 0)
        hora_inicio = evento["inicio"].astimezone(tz)
        segundos_transcurridos = int((datetime.now(tz) - hora_inicio).total_seconds())

        st.success(f"💸 Pago en proceso: {descripcion} por ${monto:,}")

        cronometro = st.empty()
        stop_button = st.button("⏹️ Finalizar pago")

        for i in range(segundos_transcurridos, segundos_transcurridos + 100000):
            if stop_button:
                coleccion.update_one(
                    {"_id": evento["_id"]},
                    {"$set": {"fin": datetime.now(tz), "en_curso": False}}
                )

                st.success("✅ Pago registrado.")
                st.rerun()

            cronometro.markdown(f"### ⏱️ Tiempo desde la intención de pago: {str(timedelta(seconds=i))}")
            time.sleep(1)

    else:
        motivo = st.text_input("Motivo del pago")
        monto = st.number_input("Monto en COP", min_value=1, step=1000)

        if st.button("🟢 Iniciar pago"):
            coleccion.insert_one({
                "tipo": "pago",
                "subtipo": motivo,
                "monto": monto,
                "inicio": datetime.now(tz),
                "en_curso": True
            })

            st.rerun()

# === HISTORIAL ESTÉTICO ===
st.subheader(f"📜 Historial de {actividad}")

filtro = {"tipo": tipo_mongo, "en_curso": False}
historial = list(coleccion.find(filtro).sort("inicio", -1))

if historial:
    for e in historial:

        inicio_dt = e["inicio"].astimezone(tz)
        fin_dt = e["fin"].astimezone(tz)

        inicio = inicio_dt.strftime('%d %b %H:%M')
        fin = fin_dt.strftime('%H:%M')

        total_segundos = int((e["fin"] - e["inicio"]).total_seconds())
        h, r = divmod(total_segundos, 3600)
        m, s = divmod(r, 60)
        duracion = f"{h:02d}:{m:02d}:{s:02d}"

        col1, col2 = st.columns([1, 7])

        with col1:
            st.markdown(
                f"<a href='?delete={e['_id']}' style='text-decoration:none; font-size:18px;'>✖</a>",
                unsafe_allow_html=True
            )

        with col2:

            if actividad == "Puntualidad":
                titulo = f"{e.get('subtipo','').capitalize()} · {e.get('puntualidad','').capitalize()}"
                extra = f"{e.get('hora_esperada','')} · {e.get('diferencia_min','')} min"

            elif actividad == "Comidas":
                titulo = e.get("subtipo","").capitalize()
                extra = ""

            elif actividad == "Pagos":
                titulo = f"${e.get('monto',0):,} · {e.get('subtipo','')}"
                extra = ""

            elif actividad == "Abstinencia":
                titulo = f"Impulso: {e.get('subtipo','')}"
                extra = ""

            else:
                titulo = actividad
                extra = ""

            st.markdown(f"**{titulo}**")

            st.caption(
                f"{inicio} → {fin} · {duracion}"
                + (f" · {extra}" if extra else "")
            )

        st.divider()

else:
    st.info("No hay registros finalizados.")