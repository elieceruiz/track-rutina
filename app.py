import streamlit as st
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

st.set_page_config("🛌 Cronómetro de Sueño")

st.title("🛌 Seguimiento de Sueño (Básico)")

# Recarga automática si hay sueño activo
if "inicio_sueno" in st.session_state and st.session_state.inicio_sueno:
    st_autorefresh(interval=1000, key="refresh_sueno")

# Inicializar estado
if "inicio_sueno" not in st.session_state:
    st.session_state.inicio_sueno = None
if "duracion_final" not in st.session_state:
    st.session_state.duracion_final = None

# Interfaz
if st.session_state.inicio_sueno:
    ahora = datetime.now()
    delta = ahora - st.session_state.inicio_sueno
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    st.markdown(f"**🕰️ Tiempo durmiendo:** {h:02}:{m:02}:{s:02}")

    if st.button("✅ Finalizar sueño"):
        st.session_state.duracion_final = delta
        st.session_state.inicio_sueno = None
else:
    if st.button("😴 Iniciar sueño"):
        st.session_state.inicio_sueno = datetime.now()
        st.session_state.duracion_final = None
        st.success("⏱️ Sueño iniciado")

# Mostrar resultado final si ya terminó
if st.session_state.duracion_final:
    d = st.session_state.duracion_final
    h, rem = divmod(int(d.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    st.success(f"🌞 Dormiste: {h} h, {m} min, {s} seg")
