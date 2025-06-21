import streamlit as st from pymongo import MongoClient from datetime import datetime, timedelta import pytz import time

Configuración

st.set_page_config("Seguimiento Diario", layout="centered") st.title("\ud83d\udcca Seguimiento de Actividades")

Zona horaria

tz = pytz.timezone("America/Bogota")

Conexión a MongoDB

MONGO_URI = st.secrets["mongo_uri"] client = MongoClient(MONGO_URI) db = client["rutina_vital"] coleccion = db["eventos"]

Lista de actividades

actividades_disponibles = [ "Sue\u00f1o", "Comidas", "Puntualidad", "Coding", "Ducha", "Leer", "Abstinencia", "Pagos" ]

Selector principal

actividad = st.selectbox("Selecciona la actividad:", actividades_disponibles)

Mapear tipos para Mongo

if actividad == "Comidas": tipo_mongo = "comida" elif actividad == "Puntualidad": tipo_mongo = "puntualidad" elif actividad == "Abstinencia": tipo_mongo = "abstinencia" elif actividad == "Pagos": tipo_mongo = "pago" else: tipo_mongo = actividad.lower()

Mostrar si hay algo en curso

en_curso_actual = coleccion.find_one({"tipo": tipo_mongo, "en_curso": True}) if en_curso_actual: hora_ini = en_curso_actual["inicio"].astimezone(tz).strftime('%H:%M:%S') descripcion = en_curso_actual.get("subtipo") or en_curso_actual.get("motivo") or actividad st.warning(f"\ud83d\udd04 Tienes un {descripcion.capitalize()} en curso desde las {hora_ini}.")

evento = None subtipo = None hora_esperada = None

Actividades con lógica estándar

if actividad in ["Sue\u00f1o", "Comidas", "Coding", "Ducha", "Leer"]: if actividad == "Comidas": subtipo_opciones = ["Desayuno", "Almuerzo", "Cena", "Snack"] evento = coleccion.find_one({"tipo": "comida", "en_curso": True}) if evento: subtipo = evento.get("subtipo", "desconocido").capitalize() else: subtipo = st.radio("Tipo de comida:", subtipo_opciones) else: evento = coleccion.find_one({"tipo": tipo_mongo, "en_curso": True})

if evento:
    hora_inicio = evento["inicio"].astimezone(tz)
    segundos_transcurridos = int((datetime.now(tz) - hora_inicio).total_seconds())
    nombre_activa = actividad if actividad != "Comidas" else subtipo
    st.success(f"{nombre_activa} iniciado a las {hora_inicio.strftime('%H:%M:%S')}")

    cronometro = st.empty()
    stop_button = st.button("\u23f9\ufe0f Finalizar")

    for i in range(segundos_transcurridos, segundos_transcurridos + 100000):
        if stop_button:
            coleccion.update_one(
                {"_id": evento["_id"]},
                {"$set": {
                    "fin": datetime.now(tz),
                    "en_curso": False
                }}
            )
            st.success("\u2705 Registro finalizado.")
            st.rerun()

        duracion = str(timedelta(seconds=i))
        cronometro.markdown(f"### \ud83d\udd52 Duraci\u00f3n: {duracion}")
        time.sleep(1)

else:
    if st.button("\ud83d\udfe2 Iniciar"):
        nuevo_evento = {
            "tipo": tipo_mongo,
            "inicio": datetime.now(tz),
            "en_curso": True
        }
        if subtipo:
            nuevo_evento["subtipo"] = subtipo.lower()
        coleccion.insert_one(nuevo_evento)
        st.rerun()

PUNTUALIDAD

elif actividad == "Puntualidad": evento = coleccion.find_one({"tipo": "puntualidad", "en_curso": True})

if evento:
    hora_inicio = evento["inicio"].astimezone(tz)
    segundos_transcurridos = int((datetime.now(tz) - hora_inicio).total_seconds())

    tipo = evento.get("subtipo", "compromiso")
    hora_esperada = evento.get("hora_esperada", "00:00")
    st.success(f"{tipo.capitalize()} — desplazamiento iniciado a las {hora_inicio.strftime('%H:%M:%S')}")
    st.info(f"Deb\u00edas llegar a las **{hora_esperada}**")

    cronometro = st.empty()
    stop_button = st.button("\u23f9\ufe0f Finalizar llegada")

    for i in range(segundos_transcurridos, segundos_transcurridos + 100000):
        if stop_button:
            ahora = datetime.now(tz)
            llegada_real = ahora.time()
            hora_obj = datetime.strptime(hora_esperada, "%H:%M").time()

            diferencia = (datetime.combine(datetime.today(), llegada_real) -
                          datetime.combine(datetime.today(), hora_obj)).total_seconds()
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
            st.success("\u2705 Llegada registrada.")
            st.rerun()

        duracion = str(timedelta(seconds=i))
        cronometro.markdown(f"### \ud83d\udeb6 Duraci\u00f3n del desplazamiento: {duracion}")
        time.sleep(1)

else:
    tipo_compromiso = st.radio("\u00bfA d\u00f3nde te diriges?", ["Clase", "Trabajo", "Cita m\u00e9dica", "Cita odontol\u00f3gica", "Otro"])
    hora_esperada = st.time_input("\u00bfA qu\u00e9 hora deber\u00edas llegar?")

    if st.button("\ud83d\udfe2 Iniciar desplazamiento"):
        ahora = datetime.now(tz)
        coleccion.insert_one({
            "tipo": "puntualidad",
            "subtipo": tipo_compromiso.lower(),
            "hora_esperada": hora_esperada.strftime("%H:%M"),
            "inicio": ahora,
            "en_curso": True
        })
        st.rerun()

ABSTINENCIA

elif actividad == "Abstinencia": opciones = [ "putas Medell\u00edn / putas Bello", "LinkedIn", "YouTube", "Apple TV+", "Domino's", "Uber", "Rapicredit", "MONET", "MAGIS" ] evento = coleccion.find_one({"tipo": "abstinencia", "en_curso": True})

if evento:
    impulso = evento.get("subtipo", "impulso")
    hora_inicio = evento["inicio"].astimezone(tz)
    segundos_transcurridos = int((datetime.now(tz) - hora_inicio).total_seconds())

    st.success(f"\ud83e\udde0 Resistencia activa contra: {impulso}")
    cronometro = st.empty()
    stop_button = st.button("\u23f9\ufe0f Finalizar contenci\u00f3n")

    for i in range(segundos_transcurridos, segundos_transcurridos + 100000):
        if stop_button:
            coleccion.update_one(
                {"_id": evento["_id"]},
                {"$set": {
                    "fin": datetime.now(tz),
                    "en_curso": False
                }}
            )
            st.success("\u2705 Contenci\u00f3n registrada.")
            st.rerun()

        duracion = str(timedelta(seconds=i))
        cronometro.markdown(f"### \u23f1\ufe0f Tiempo resistido: {duracion}")
        time.sleep(1)
else:
    impulso = st.radio("\u00bfCu\u00e1l impulso est\u00e1s resistiendo?", opciones)
    if st.button("\ud83d\udfe2 Registrar impulso"):
        coleccion.insert_one({
            "tipo": "abstinencia",
            "subtipo": impulso,
            "inicio": datetime.now(tz),
            "en_curso": True
        })
        st.rerun()

PAGOS

elif actividad == "Pagos": evento = coleccion.find_one({"tipo": "pago", "en_curso": True})

if evento:
    motivo = evento.get("motivo", "sin motivo")
    monto = evento.get("monto", 0)
    hora_inicio = evento["inicio"].astimezone(tz)
    segundos_transcurridos = int((datetime.now(tz) - hora_inicio).total_seconds())

    st.success(f"\ud83d\udcb0 {motivo} por {monto:,} COP iniciado a las {hora_inicio.strftime('%H:%M:%S')}")
    cronometro = st.empty()
    stop_button = st.button("\u23f9\ufe0f Finalizar registro de pago")

    for i in range(segundos_transcurridos, segundos_transcurridos + 100000):
        if stop_button:
            coleccion.update_one(
                {"_id": evento["_id"]},
                {"$set": {
                    "fin": datetime.now(tz),
                    "en_curso": False
                }}
            )
            st.success("\u2705 Pago registrado.")
            st.rerun()

        duracion = str(timedelta(seconds=i))
        cronometro.markdown(f"### \u23f1\ufe0f Tiempo desde decisi\u00f3n hasta pago: {duracion}")
        time.sleep(1)
else:
    motivo = st.text_input("Motivo del pago:")
    monto = st.number_input("Monto en COP:", min_value=0, step=1000)

    if motivo and monto > 0 and st.button("\ud83d\udfe2 Registrar intenci\u00f3n de pago"):
        coleccion.insert_one({
            "tipo": "pago",
            "motivo": motivo,
            "monto": monto,
            "inicio": datetime.now(tz),
            "en_curso": True
        })
        st.rerun()

HISTORIAL

st.subheader(f"\ud83d\udcdc Historial de {actividad}")

filtro = {"tipo": tipo_mongo, "en_curso": False} historial = list(coleccion.find(filtro).sort("inicio", -1))

if historial: data = [] for evento in historial: inicio = evento["inicio"].astimezone(tz).strftime('%Y-%m-%d %H:%M:%S') fin = evento["fin"].astimezone(tz).strftime('%Y-%m-%d %H:%M:%S') total_segundos = int((evento["fin"] - evento["inicio"]).total_seconds()) horas, resto = divmod(total_segundos, 3600) minutos, segundos = divmod(resto, 60) duracion = f"{horas:02d}h {minutos:02d}m {segundos:02d}s"

fila = {"Inicio": inicio, "Fin": fin, "Duraci\u00f3n": duracion}

    if actividad == "Comidas":
        fila["Comida"] = evento.get("subtipo", "desconocido").capitalize()
    elif actividad == "Puntualidad":
        fila["Compromiso"] = evento.get("subtipo", "desconocido").capitalize()
        fila["Esperada"] = evento.get("hora_esperada", "")
        fila["Puntualidad"] = evento.get("puntualidad", "desconocido").capitalize()
        fila["Diferencia (min)"] = evento.get("diferencia_min", "")
    elif actividad == "Abstinencia":
        fila["Impulso"] = evento.get("subtipo", "desconocido")
    elif actividad == "Pagos":
        fila["Motivo"] = evento.get("motivo", "desconocido")
        fila["Monto (COP)"] = f'{evento.get("monto", 0):,}'

    data.append(fila)

st.dataframe(data, use_container_width=True)

else: st.info("No hay registros finalizados.")

