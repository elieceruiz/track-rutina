import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta, time as dtime
import pytz
import time

# Configuración
st.set_page_config("Seguimiento Diario", layout="centered")
st.title("📊 Seguimiento de Actividades")

# Zona horaria
tz = pytz.timezone("America/Bogota")

# Conexión a MongoDB
MONGO_URI = st.secrets["mongo_uri"]
client = MongoClient(MONGO_URI)
db = client["rutina_vital"]
coleccion = db["eventos"]

# Selector de actividad
actividad = st.selectbox("Selecciona la actividad:", ["Sueño", "Comidas", "Puntualidad"])

evento = None
subtipo = None
hora_esperada = None

# ------------------------------------------
# 🍽️ COMIDAS y 💤 SUEÑO (lógica con cronómetro)
# ------------------------------------------
if actividad in ["Sueño", "Comidas"]:
    if actividad == "Comidas":
        subtipo_opciones = ["Desayuno", "Almuerzo", "Cena", "Snack"]
        evento = coleccion.find_one({"tipo": "comida", "en_curso": True})
        if evento:
            subtipo = evento.get("subtipo", "desconocido").capitalize()
        else:
            subtipo = st.radio("Tipo de comida:", subtipo_opciones)
    else:
        evento = coleccion.find_one({"tipo": "sueño", "en_curso": True})

    if evento:
        hora_inicio = evento["inicio"].astimezone(tz)
        segundos_transcurridos = int((datetime.now(tz) - hora_inicio).total_seconds())

        nombre_activa = actividad if actividad == "Sueño" else subtipo
        st.success(f"{nombre_activa} iniciado a las {hora_inicio.strftime('%H:%M:%S')}")

        cronometro = st.empty()
        stop_button = st.button("⏹️ Finalizar")

        for i in range(segundos_transcurridos, segundos_transcurridos + 100000):
            if stop_button:
                coleccion.update_one(
                    {"_id": evento["_id"]},
                    {
                        "$set": {
                            "fin": datetime.now(tz),
                            "en_curso": False
                        }
                    }
                )
                st.success("✅ Registro finalizado.")
                st.rerun()

            duracion = str(timedelta(seconds=i))
            cronometro.markdown(f"### 🕒 Duración: {duracion}")
            time.sleep(1)

    else:
        if st.button("🟢 Iniciar"):
            nuevo_evento = {
                "tipo": "comida" if actividad == "Comidas" else "sueño",
                "inicio": datetime.now(tz),
                "en_curso": True
            }
            if subtipo:
                nuevo_evento["subtipo"] = subtipo.lower()
            coleccion.insert_one(nuevo_evento)
            st.rerun()

# ------------------------------------------
# ⏰ PUNTUALIDAD
# ------------------------------------------
elif actividad == "Puntualidad":
    evento = coleccion.find_one({"tipo": "puntualidad", "en_curso": True})

    if evento:
        hora_inicio = evento["inicio"].astimezone(tz)
        segundos_transcurridos = int((datetime.now(tz) - hora_inicio).total_seconds())

        puntualidad = evento.get("puntualidad", "desconocido").capitalize()
        tipo = evento.get("subtipo", "compromiso")
        esperada = evento.get("hora_esperada")

        st.success(f"{tipo.capitalize()} iniciado a las {hora_inicio.strftime('%H:%M:%S')}")
        st.info(f"⏱️ Llegaste **{puntualidad}** respecto a la hora esperada: {esperada}")

        cronometro = st.empty()
        stop_button = st.button("⏹️ Finalizar compromiso")

        for i in range(segundos_transcurridos, segundos_transcurridos + 100000):
            if stop_button:
                coleccion.update_one(
                    {"_id": evento["_id"]},
                    {
                        "$set": {
                            "fin": datetime.now(tz),
                            "en_curso": False
                        }
                    }
                )
                st.success("✅ Compromiso finalizado.")
                st.rerun()

            duracion = str(timedelta(seconds=i))
            cronometro.markdown(f"### 🕒 Duración: {duracion}")
            time.sleep(1)

    else:
        tipo_compromiso = st.radio("¿Qué tipo de compromiso es?", ["Clase", "Trabajo", "Cita médica", "Cita odontológica", "Otro"])
        hora_esperada = st.time_input("¿A qué hora deberías haber llegado?")

        if st.button("🟢 Registrar llegada"):
            ahora = datetime.now(tz)
            llegada = ahora.time()
            puntualidad = "temprano" if llegada <= hora_esperada else "tarde"

            coleccion.insert_one({
                "tipo": "puntualidad",
                "subtipo": tipo_compromiso.lower(),
                "hora_esperada": hora_esperada.strftime("%H:%M"),
                "inicio": ahora,
                "puntualidad": puntualidad,
                "en_curso": True
            })
            st.rerun()

# ------------------------------------------
# 📜 HISTORIAL
# ------------------------------------------

st.subheader(f"📜 Historial de {actividad}")

filtro = {"tipo": actividad.lower(), "en_curso": False}
historial = list(coleccion.find(filtro).sort("inicio", -1))

if historial:
    data = []
    for evento in historial:
        inicio = evento["inicio"].astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')
        fin = evento["fin"].astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')
        total_segundos = int((evento["fin"] - evento["inicio"]).total_seconds())
        horas, resto = divmod(total_segundos, 3600)
        minutos, segundos = divmod(resto, 60)
        duracion = f"{horas:02d}h {minutos:02d}m {segundos:02d}s"

        fila = {"Inicio": inicio, "Fin": fin, "Duración": duracion}

        if actividad == "Comidas":
            fila["Comida"] = evento.get("subtipo", "desconocido").capitalize()
        elif actividad == "Puntualidad":
            fila["Compromiso"] = evento.get("subtipo", "desconocido").capitalize()
            fila["Esperada"] = evento.get("hora_esperada", "")
            fila["Puntualidad"] = evento.get("puntualidad", "desconocido").capitalize()

        data.append(fila)

    st.dataframe(data, use_container_width=True)
else:
    st.info("No hay registros finalizados.")