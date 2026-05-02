import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import time
from bson import ObjectId

# === CONFIGURACIÓN GENERAL ===
st.set_page_config("Contención", layout="centered")
st.title("📊 Contención")

tz = pytz.timezone("America/Bogota")

MONGO_URI = st.secrets["mongo_uri"]
client = MongoClient(MONGO_URI)
db = client["rutina_vital"]
coleccion = db["eventos"]

actividades_disponibles = [
    "Sueño", "Comidas", "Puntualidad", "Coding", "Ducha", "Leer", "Abstinencia", "Pagos"
]

actividad = st.selectbox("Selecciona la actividad:", actividades_disponibles)

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

en_curso_actual = coleccion.find_one({"tipo": tipo_mongo, "en_curso": True})
if en_curso_actual:
    hora_ini = en_curso_actual["inicio"].astimezone(tz).strftime('%H:%M:%S')
    descripcion = en_curso_actual.get("subtipo", actividad).capitalize()
    st.warning(f"🔄 Tienes un **{descripcion}** en curso desde las {hora_ini}.")

evento = None
subtipo = None

# === BLOQUE 1 ===
if actividad in ["Sueño", "Comidas", "Coding", "Ducha", "Leer"]:
    if actividad == "Comidas":
        opciones = ["Desayuno", "Almuerzo", "Cena", "Snack"]
        evento = coleccion.find_one({"tipo": "comida", "en_curso": True})
        subtipo = evento.get("subtipo").capitalize() if evento else st.radio("Tipo de comida:", opciones)
    else:
        evento = coleccion.find_one({"tipo": tipo_mongo, "en_curso": True})

    if evento:
        inicio = evento["inicio"].astimezone(tz)
        segundos = int((datetime.now(tz) - inicio).total_seconds())

        st.success(f"Iniciado a las {inicio.strftime('%H:%M:%S')}")
        cronometro = st.empty()
        stop = st.button("⏹️ Finalizar")

        for i in range(segundos, segundos + 100000):
            if stop:
                coleccion.update_one(
                    {"_id": evento["_id"]},
                    {"$set": {"fin": datetime.now(tz), "en_curso": False}}
                )
                st.success("✅ Finalizado")
                st.rerun()

            cronometro.markdown(f"### 🕒 {str(timedelta(seconds=i))}")
            time.sleep(1)

    else:
        if st.button("🟢 Iniciar"):
            nuevo = {"tipo": tipo_mongo, "inicio": datetime.now(tz), "en_curso": True}
            if subtipo:
                nuevo["subtipo"] = subtipo.lower()
            coleccion.insert_one(nuevo)
            st.rerun()

# === PUNTUALIDAD ===
elif actividad == "Puntualidad":
    evento = coleccion.find_one({"tipo": "puntualidad", "en_curso": True})

    if evento:
        inicio = evento["inicio"].astimezone(tz)
        segundos = int((datetime.now(tz) - inicio).total_seconds())

        st.success(f"Salida a las {inicio.strftime('%H:%M:%S')}")
        st.info(f"Llegada esperada: {evento.get('hora_esperada')}")

        cronometro = st.empty()
        stop = st.button("⏹️ Finalizar llegada")

        for i in range(segundos, segundos + 100000):
            if stop:
                ahora = datetime.now(tz)
                llegada = ahora.time()
                esperada = datetime.strptime(evento["hora_esperada"], "%H:%M").time()

                diff = (datetime.combine(datetime.today(), llegada) -
                        datetime.combine(datetime.today(), esperada)).total_seconds()

                coleccion.update_one(
                    {"_id": evento["_id"]},
                    {"$set": {
                        "fin": ahora,
                        "en_curso": False,
                        "puntualidad": "temprano" if diff <= 0 else "tarde",
                        "diferencia_min": round(diff / 60)
                    }}
                )

                st.success("✅ Registrado")
                st.rerun()

            cronometro.markdown(f"### 🚶 {str(timedelta(seconds=i))}")
            time.sleep(1)

    else:
        tipo = st.radio("Destino:", ["Clase", "Trabajo", "Cita médica", "Otro"])
        hora = st.time_input("Hora esperada")

        if st.button("🟢 Iniciar"):
            coleccion.insert_one({
                "tipo": "puntualidad",
                "subtipo": tipo.lower(),
                "hora_esperada": hora.strftime("%H:%M"),
                "inicio": datetime.now(tz),
                "en_curso": True
            })
            st.rerun()

# === ABSTINENCIA ===
elif actividad == "Abstinencia":
    opciones = ["LinkedIn", "YouTube", "Apple TV+", "Uber", "Domino's", "Otros"]

    evento = coleccion.find_one({"tipo": "abstinencia", "en_curso": True})

    if evento:
        inicio = evento["inicio"].astimezone(tz)
        segundos = int((datetime.now(tz) - inicio).total_seconds())

        st.success(f"Resistiendo: {evento.get('subtipo')}")

        cronometro = st.empty()
        stop = st.button("⏹️ Finalizar")

        for i in range(segundos, segundos + 100000):
            if stop:
                coleccion.update_one(
                    {"_id": evento["_id"]},
                    {"$set": {"fin": datetime.now(tz), "en_curso": False}}
                )
                st.success("✅ Registrado")
                st.rerun()

            cronometro.markdown(f"### ⏱️ {str(timedelta(seconds=i))}")
            time.sleep(1)

    else:
        impulso = st.radio("Impulso:", opciones)
        if st.button("🟢 Registrar"):
            coleccion.insert_one({
                "tipo": "abstinencia",
                "subtipo": impulso,
                "inicio": datetime.now(tz),
                "en_curso": True
            })
            st.rerun()

# === PAGOS ===
elif actividad == "Pagos":
    evento = coleccion.find_one({"tipo": "pago", "en_curso": True})

    if evento:
        inicio = evento["inicio"].astimezone(tz)
        segundos = int((datetime.now(tz) - inicio).total_seconds())

        st.success(f"${evento.get('monto'):,} — {evento.get('subtipo')}")

        cronometro = st.empty()
        stop = st.button("⏹️ Finalizar")

        for i in range(segundos, segundos + 100000):
            if stop:
                coleccion.update_one(
                    {"_id": evento["_id"]},
                    {"$set": {"fin": datetime.now(tz), "en_curso": False}}
                )
                st.success("✅ Registrado")
                st.rerun()

            cronometro.markdown(f"### ⏱️ {str(timedelta(seconds=i))}")
            time.sleep(1)

    else:
        motivo = st.text_input("Motivo")
        monto = st.number_input("Monto", min_value=1)

        if st.button("🟢 Iniciar"):
            coleccion.insert_one({
                "tipo": "pago",
                "subtipo": motivo,
                "monto": monto,
                "inicio": datetime.now(tz),
                "en_curso": True
            })
            st.rerun()

# === HISTORIAL (FORMATO MÓVIL) ===
st.subheader(f"📜 Historial de {actividad}")

historial = list(coleccion.find({"tipo": tipo_mongo, "en_curso": False}).sort("inicio", -1))

if historial:
    for e in historial:

        inicio = e["inicio"].astimezone(tz)
        fin = e["fin"].astimezone(tz)

        duracion = str(timedelta(seconds=int((e["fin"] - e["inicio"]).total_seconds())))

        col1, col2 = st.columns([1, 5])

        with col1:
            if st.button("❌", key=f"del_{e['_id']}"):
                coleccion.delete_one({"_id": ObjectId(e["_id"])})
                st.rerun()

        with col2:
            st.markdown(f"""
            **Inicio:** {inicio.strftime('%Y-%m-%d %H:%M:%S')}  
            **Fin:** {fin.strftime('%Y-%m-%d %H:%M:%S')}  
            **Duración:** {duracion}  
            """)

            if actividad == "Comidas":
                st.markdown(f"**Comida:** {e.get('subtipo','')}")
            elif actividad == "Puntualidad":
                st.markdown(f"""
                **Compromiso:** {e.get('subtipo','')}  
                **Esperada:** {e.get('hora_esperada','')}  
                **Puntualidad:** {e.get('puntualidad','')}  
                **Diferencia:** {e.get('diferencia_min','')} min
                """)
            elif actividad == "Abstinencia":
                st.markdown(f"**Impulso:** {e.get('subtipo','')}")
            elif actividad == "Pagos":
                st.markdown(f"**Monto:** ${e.get('monto',0):,} — {e.get('subtipo','')}")

        st.divider()

else:
    st.info("No hay registros.")