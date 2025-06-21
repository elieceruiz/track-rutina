import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
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
actividad = st.selectbox("Selecciona la actividad:", ["Sueño", "Comidas"])

# ------------------------------------------
# 💤 SUEÑO o 🍽️ COMIDAS con misma lógica
# ------------------------------------------

# Manejo de comidas con subtipo persistente
subtipo = None
if actividad == "Comidas":
    evento = coleccion.find_one({"tipo": "comida", "en_curso": True})
    subtipo_opciones = ["Desayuno", "Almuerzo", "Cena", "Snack"]

    if evento:
        subtipo = evento.get("subtipo", "desconocido").capitalize()
    else:
        subtipo = st.radio("Tipo de comida:", subtipo_opciones)
        evento = None
else:
    evento = coleccion.find_one({"tipo": "sueño", "en_curso": True})

# Evento activo
if evento:
    hora_inicio = evento["inicio"].astimezone(tz)
    segundos_transcurridos = int((datetime.now(tz) - hora_inicio).total_seconds())

    nombre_actividad = actividad if actividad == "Sueño" else subtipo
    st.success(f"{nombre_actividad} iniciado a las {hora_inicio.strftime('%H:%M:%S')}")

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

# Iniciar nuevo evento
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
# 📜 Historial
# ------------------------------------------

st.subheader(f"📜 Historial de {actividad}")

filtro_historial = {"tipo": "comida"} if actividad == "Comidas" else {"tipo": "sueño"}
filtro_historial["en_curso"] = False

historial = list(coleccion.find(filtro_historial).sort("inicio", -1))

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
        data.append(fila)

    st.dataframe(data, use_container_width=True)
else:
    st.info("No hay registros finalizados.")