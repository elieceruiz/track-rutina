import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
from zoneinfo import ZoneInfo
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# Zona horaria
ZONA = ZoneInfo("America/Bogota")

# Conexión a MongoDB
client = MongoClient(st.secrets["mongo_uri"])
db = client["seguimiento_sueno"]
col_sueno = db["sueno"]

# Inicializar estado
if "inicio_sueno" not in st.session_state:
    st.session_state.inicio_sueno = None
if "id_sueno_en_curso" not in st.session_state:
    st.session_state.id_sueno_en_curso = None
if "finalizado" not in st.session_state:
    st.session_state.finalizado = False

# Función para mostrar cronómetro
def mostrar_cronometro(inicio):
    delta = datetime.now(ZONA) - inicio
    h, rem = divmod(delta.seconds, 3600)
    m, s = divmod(rem, 60)
    st.markdown(f"**🕒 Duración del sueño:** {h:02}:{m:02}:{s:02}")

# Título de la app
st.title("🛌 Seguimiento de sueño")
st.caption("Controla en tiempo real cuánto duermes cada noche.")

# Restaurar estado si hay sueño en curso en Mongo
en_curso = col_sueno.find_one({"en_progreso": True})
if en_curso and not st.session_state.inicio_sueno:
    st.session_state.inicio_sueno = datetime.strptime(en_curso["inicio"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
    st.session_state.id_sueno_en_curso = en_curso["_id"]

# Iniciar nuevo sueño
if not st.session_state.inicio_sueno:
    if st.button("😴 Iniciar sueño"):
        ahora = datetime.now(ZONA)
        resultado = col_sueno.insert_one({
            "inicio": ahora.strftime("%Y-%m-%d %H:%M:%S"),
            "fecha": ahora.strftime("%Y-%m-%d"),
            "en_progreso": True
        })
        st.session_state.inicio_sueno = ahora
        st.session_state.id_sueno_en_curso = resultado.inserted_id
        st.session_state.finalizado = False
        st.success("⏱️ Cronómetro de sueño iniciado")

# Mostrar cronómetro si está en curso
if st.session_state.inicio_sueno and not st.session_state.finalizado:
    st_autorefresh(interval=1000, key="refresh_sueno")
    mostrar_cronometro(st.session_state.inicio_sueno)

    if st.button("🌞 Finalizar sueño"):
        fin = datetime.now(ZONA)
        duracion_td = fin - st.session_state.inicio_sueno
        duracion_horas = round(duracion_td.total_seconds() / 3600, 2)
        duracion_str = str(timedelta(seconds=int(duracion_td.total_seconds())))

        try:
            resultado = col_sueno.update_one(
                {"_id": st.session_state.id_sueno_en_curso, "en_progreso": True},
                {"$set": {
                    "fin": fin.strftime("%Y-%m-%d %H:%M:%S"),
                    "duracion_horas": duracion_horas,
                    "duracion_str": duracion_str,
                    "en_progreso": False
                }}
            )
        except Exception as e:
            st.error(f"❌ Error al actualizar en MongoDB: {e}")
        else:
            if resultado.modified_count == 1:
                st.session_state.finalizado = True
                st.session_state.inicio_sueno = None
                st.session_state.id_sueno_en_curso = None
                st.success(f"✅ Sueño finalizado: {duracion_str}")
                st.experimental_rerun()
            else:
                st.error("⚠️ No se encontró sesión activa para finalizar.")

# Mostrar mensaje si ya se finalizó
if st.session_state.finalizado:
    st.info("✔️ Tu última sesión fue finalizada correctamente.")

# Historial de sesiones
st.subheader("📊 Historial de sueño")
historial = list(col_sueno.find({"en_progreso": False}, {"_id": 0}).sort("inicio", -1))
if historial:
    df = pd.DataFrame(historial)
    columnas = [col for col in ["fecha", "inicio", "fin", "duracion_str"] if col in df.columns]
    st.dataframe(df[columnas])
else:
    st.info("Aún no tienes registros finalizados.")
