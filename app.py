import streamlit as st
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

st.set_page_config("🛌 Sueño Cronómetro Básico")

st.title("🛌 Cronómetro de Sueño")

# 1. Si hay un inicio registrado, activa refresco cada 1 segundo
if st.session_state.get("inicio_sueno"):
    st_autorefresh(interval=1000, key="auto_refresh")

# 2. Si no hay registro, crea variables
if "inicio_sueno" not in st.session_state:
    st.session_state.inicio_sueno = None
if "duracion_final" not in st.session_state:
    st.session_state.duracion_final = None

# 3. Mostrar cronómetro en curso
if st.session_state.inicio_sueno:
    ahora = datetime.now()
    delta = ahora - st.session_state.inicio_sueno
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    st.markdown(f"**🕰️ Tiempo durmiendo:** {h:02}:{m:02}:{s:02}")

    if st.button("✅ Finalizar sueño"):
        st.session_state.duracion_final = delta
        st.session_state.inicio_sueno = None

# 4. Mostrar botón de inicio
elif not st.session_state.duracion_final:
    if st.button("😴 Iniciar sueño"):
        st.session_state.inicio_sueno = datetime.now()
        st.rerun()  # ← esto es lo que faltaba: refresca para que el cronómetro empiece YA

# 5. Mostrar resultado final
if st.session_state.duracion_final:
    d = st.session_state.duracion_final
    h, rem = divmod(int(d.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    st.success(f"🌞 Dormiste: {h} h, {m} min, {s} seg")
