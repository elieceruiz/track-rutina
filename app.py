import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import time

# Configuración inicial
st.set_page_config("Seguimiento de Sueño", layout="centered")
st.title("🛌 Seguimiento de Sueño")

# Zona horaria
tz = pytz.timezone("America/Bogota")

# Conexión a MongoDB desde secrets
MONGO_URI = st.secrets["mongo_uri"]
client = MongoClient(MONGO_URI)
db = client["rutina_vital"]
coleccion = db["eventos"]

# Buscar evento en curso
evento = coleccion.find_one({"tipo": "sueño", "en_curso": True})

# Si hay evento activo
if evento:
    hora_inicio = evento["inicio"].astimezone(tz)
    segundos_transcurridos = int((datetime.now(tz) - hora_inicio).total_seconds())

    st.success(f"Sueño iniciado a las {hora_inicio.strftime('%H:%M:%S')}")

    cronometro = st.empty()
    stop_button = st.button("⏹️ Finalizar Sueño")

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
            st.success("✅ Sueño finalizado.")
            st.rerun()

        duracion = str(timedelta(seconds=i))
        cronometro.markdown(f"### 🕒 Duración: {duracion}")
        time.sleep(1)

# Si no hay evento en curso
else:
    if st.button("🌙 Iniciar Sueño"):
        coleccion.insert_one({
            "tipo": "sueño",
            "inicio": datetime.now(tz),
            "en_curso": True
        })
        st.rerun()

# Mostrar historial de eventos finalizados
st.subheader("📜 Historial de Sueño Finalizado")

historial = list(
    coleccion.find({"tipo": "sueño", "en_curso": False}).sort("inicio", -1)
)

if historial:
    data = []
    for evento in historial:
        inicio = evento["inicio"].astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')
        fin = evento["fin"].astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')
        total_segundos = int((evento["fin"] - evento["inicio"]).total_seconds())
        horas, resto = divmod(total_segundos, 3600)
        minutos, segundos = divmod(resto, 60)
        duracion = f"{horas:02d}h {minutos:02d}m {segundos:02d}s"
        data.append({"Inicio": inicio, "Fin": fin, "Duración": duracion})

    st.dataframe(data, use_container_width=True)
else:
    st.info("No hay registros finalizados.")