import streamlit as st
from datetime import datetime
from pymongo import MongoClient

st.set_page_config("Test Mongo")

st.title("🧪 Prueba directa con Mongo")

# Conexión
try:
    client = MongoClient(st.secrets["mongo_uri"])
    db = client["test"]
    col = db["ping"]
except Exception as e:
    st.error(f"❌ No se pudo conectar a Mongo: {e}")
    st.stop()

# Estado inicial
if "inicio" not in st.session_state:
    st.session_state.inicio = None

# Botón
if st.button("Iniciar prueba"):
    ahora = datetime.now()
    try:
        resultado = col.insert_one({
            "accion": "inicio_prueba",
            "timestamp": ahora.strftime("%Y-%m-%d %H:%M:%S")
        })
        st.session_state.inicio = ahora
        st.success(f"✅ Guardado: {ahora}")
        st.experimental_rerun()
    except Exception as e:
        st.error(f"❌ Error insertando en Mongo: {e}")

# Ver estado
if st.session_state.inicio:
    st.info(f"Sesión iniciada: {st.session_state.inicio}")
