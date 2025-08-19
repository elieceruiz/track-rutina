import json
import time
from datetime import datetime, timedelta

import pytz
import streamlit as st
import streamlit.components.v1 as components
from pymongo import MongoClient
from webauthn import (
    generate_registration_options,
    generate_authentication_options,
    verify_registration_response,
    verify_authentication_response,
)
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor,
    UserVerificationRequirement,
)

# =========================
# CONFIGURACIÓN GENERAL
# =========================
st.set_page_config(page_title="Seguimiento Diario", layout="centered")
tz = pytz.timezone("America/Bogota")

# --- MongoDB
MONGO_URI = st.secrets["mongo"]["uri"]
client = MongoClient(MONGO_URI)
db = client["rutina_vital"]
coleccion = db["eventos"]
usuarios_col = db["usuarios"]  # { email, credential_id, credential_public_key, sign_count }

# --- WebAuthn (Passkeys)
RP_ID = st.secrets["auth"]["rp_id"]
RP_NAME = st.secrets["auth"]["rp_name"]
ORIGIN = st.secrets["auth"]["origin"]


# =========================
# HELPERS: HTML COMPONENT (WebAuthn bridge)
# =========================
def webauthn_component(action: str, options_json: str, height: int = 0):
    """
    Renderiza un componente HTML que ejecuta navigator.credentials.create/get
    con las 'options' proporcionadas (JSON con base64url) y retorna la respuesta
    serializada (JSON base64url) a Streamlit.

    Devuelve: dict (respuesta WebAuthn) o None.
    """
    html = f"""
    <script>
    // --- utils base64url <-> ArrayBuffer
    function b64urlToBuf(b64url) {{
      const pad = "=".repeat((4 - (b64url.length % 4)) % 4);
      const b64 = (b64url.replace(/-/g, "+").replace(/_/g, "/")) + pad;
      const str = atob(b64);
      const buf = new ArrayBuffer(str.length);
      const bytes = new Uint8Array(buf);
      for (let i = 0; i < str.length; i++) bytes[i] = str.charCodeAt(i);
      return buf;
    }}
    function bufToB64url(buf) {{
      const bytes = new Uint8Array(buf);
      let str = "";
      for (let i = 0; i < bytes.byteLength; i++) str += String.fromCharCode(bytes[i]);
      let b64 = btoa(str).replace(/\\+/g, "-").replace(/\\//g, "_").replace(/=+$/, "");
      return b64;
    }}

    async function run() {{
      const opts = {options_json};

      if ("publicKey" in opts) {{
        // Convertir campos binarios base64url -> ArrayBuffer
        if (opts.publicKey.challenge) {{
          opts.publicKey.challenge = b64urlToBuf(opts.publicKey.challenge);
        }}
        if (opts.publicKey.user && opts.publicKey.user.id) {{
          opts.publicKey.user.id = b64urlToBuf(opts.publicKey.user.id);
        }}
        if (opts.publicKey.allowCredentials) {{
          for (const cred of opts.publicKey.allowCredentials) {{
            if (cred.id) cred.id = b64urlToBuf(cred.id);
          }}
        }}
        if (opts.publicKey.excludeCredentials) {{
          for (const cred of opts.publicKey.excludeCredentials) {{
            if (cred.id) cred.id = b64urlToBuf(cred.id);
          }}
        }}
      }}

      try {{
        let cred;
        if ("{action}" === "create") {{
          cred = await navigator.credentials.create(opts);
        }} else {{
          cred = await navigator.credentials.get(opts);
        }}

        // Serializar respuesta (buffers -> base64url)
        const toJSON = (c) => {{
          if (!c) return null;
          const json = {{
            id: c.id,
            type: c.type,
            rawId: bufToB64url(c.rawId),
          }};
          if (c.response) {{
            json.response = {{}};
            if (c.response.clientDataJSON) {{
              json.response.clientDataJSON = bufToB64url(c.response.clientDataJSON);
            }}
            if (c.response.attestationObject) {{
              json.response.attestationObject = bufToB64url(c.response.attestationObject);
            }}
            if (c.response.authenticatorData) {{
              json.response.authenticatorData = bufToB64url(c.response.authenticatorData);
            }}
            if (c.response.signature) {{
              json.response.signature = bufToB64url(c.response.signature);
            }}
            if (c.response.userHandle) {{
              json.response.userHandle = bufToB64url(c.response.userHandle);
            }}
            if (c.response.publicKey) {{
              json.response.publicKey = bufToB64url(c.response.publicKey);
            }}
            if (c.response.transports) {{
              json.response.transports = c.response.transports;
            }}
          }}
          if (c.authenticatorAttachment) {{
            json.authenticatorAttachment = c.authenticatorAttachment;
          }}
          if (c.clientExtensionResults) {{
            json.clientExtensionResults = c.clientExtensionResults;
          }}
          return json;
        }};

        const out = toJSON(cred);

        // Enviar valor de vuelta a Streamlit
        const payload = {{
          isStreamlitMessage: true,
          type: "streamlit:setComponentValue",
          value: out
        }};
        window.parent.postMessage(payload, "*");
      }} catch (e) {{
        const payload = {{
          isStreamlitMessage: true,
          type: "streamlit:setComponentValue",
          value: {{ error: String(e) }}
        }};
        window.parent.postMessage(payload, "*");
      }}
    }}

    run();
    </script>
    """
    return components.html(html, height=height)


def options_to_json_for_component(options_obj) -> str:
    """
    Convierte el objeto de opciones (pydantic) a JSON plano.
    .model_dump() ya trae campos en base64url para binarios.
    """
    try:
        data = options_obj.model_dump()
    except Exception:
        # versiones antiguas
        from webauthn.helpers import options_to_json as _to_json_str

        return _to_json_str(options_obj)
    return json.dumps(data)


# =========================
# ESTADO DE SESIÓN
# =========================
if "current_user" not in st.session_state:
    st.session_state["current_user"] = None


# =========================
# UI: AUTENTICACIÓN PASSKEY
# =========================
if not st.session_state["current_user"]:
    st.title("🔒 Autenticación con Passkey (Huella / Windows Hello)")

    tab_reg, tab_login = st.tabs(["🆕 Registrar Passkey", "🔑 Iniciar Sesión"])

    with tab_reg:
        email_reg = st.text_input("Correo a registrar")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("1) Generar reto de registro"):
                if not email_reg:
                    st.error("Ingresa un correo.")
                else:
                    reg_opts = generate_registration_options(
                        rp_id=RP_ID,
                        rp_name=RP_NAME,
                        user_id=email_reg.encode("utf-8"),
                        user_name=email_reg,
                    )
                    st.session_state["reg_opts"] = reg_opts
                    st.success("Reto generado. Disparando biometría...")
                    # Ejecutar WebAuthn.create en el navegador
                    options_json = options_to_json_for_component(reg_opts)
                    resp = webauthn_component("create", options_json)
                    st.session_state["reg_resp"] = resp

        with col2:
            if st.button("2) Verificar y guardar Passkey"):
                reg_opts = st.session_state.get("reg_opts")
                resp = st.session_state.get("reg_resp")
                if not reg_opts or not resp:
                    st.error("Primero genera el reto (paso 1).")
                else:
                    if isinstance(resp, dict) and resp.get("error"):
                        st.error(f"Navegador: {resp.get('error')}")
                    else:
                        try:
                            verification = verify_registration_response(
                                credential=resp,
                                expected_challenge=reg_opts.challenge,
                                expected_origin=ORIGIN,
                                expected_rp_id=RP_ID,
                            )
                            # Guardar en Mongo
                            usuarios_col.update_one(
                                {"email": email_reg},
                                {
                                    "$set": {
                                        "email": email_reg,
                                        "credential_id": resp.get("id"),
                                        "credential_public_key": verification.credential_public_key,
                                        "sign_count": verification.sign_count if hasattr(verification, "sign_count") else 0,
                                    }
                                },
                                upsert=True,
                            )
                            st.success("✅ Passkey registrada correctamente.")
                        except Exception as e:
                            st.error(f"Error verificando registro: {e}")

    with tab_login:
        email_login = st.text_input("Correo para iniciar sesión")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("1) Generar reto de login"):
                if not email_login:
                    st.error("Ingresa tu correo.")
                else:
                    # Buscar credencial para restringir allowCredentials (opcional)
                    user = usuarios_col.find_one({"email": email_login})
                    allow = None
                    if user and user.get("credential_id"):
                        allow = [
                            PublicKeyCredentialDescriptor(id=user["credential_id"], type="public-key")
                        ]
                    auth_opts = generate_authentication_options(
                        rp_id=RP_ID,
                        user_verification=UserVerificationRequirement.PREFERRED,
                        allow_credentials=allow,
                    )
                    st.session_state["auth_opts"] = auth_opts
                    st.success("Reto generado. Disparando biometría...")
                    options_json = options_to_json_for_component(auth_opts)
                    resp = webauthn_component("get", options_json)
                    st.session_state["auth_resp"] = resp

        with col2:
            if st.button("2) Verificar login"):
                auth_opts = st.session_state.get("auth_opts")
                resp = st.session_state.get("auth_resp")
                if not auth_opts or not resp:
                    st.error("Primero genera el reto (paso 1).")
                else:
                    if isinstance(resp, dict) and resp.get("error"):
                        st.error(f"Navegador: {resp.get('error')}")
                    else:
                        try:
                            user = usuarios_col.find_one({"email": email_login})
                            if not user:
                                st.error("Usuario no registrado.")
                            else:
                                verify_authentication_response(
                                    credential=resp,
                                    expected_challenge=auth_opts.challenge,
                                    expected_origin=ORIGIN,
                                    expected_rp_id=RP_ID,
                                    credential_public_key=user["credential_public_key"],
                                    credential_current_sign_count=int(user.get("sign_count", 0)),
                                )
                                # (Opcional) Actualizar sign_count si tu verificador lo devuelve
                                st.session_state["current_user"] = email_login
                                st.success(f"🎉 Bienvenido {email_login}")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error verificando login: {e}")

    st.stop()  # 🚫 No carga la app si no hay login


# =========================
# APP PRINCIPAL (TU CÓDIGO ORIGINAL)
# =========================

st.title("📊 Seguimiento de Actividades")

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
# Sueño, Comidas, Coding, Ducha, Leer
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
                diferencia = (datetime.combine(datetime.today(), llegada_real) - datetime.combine(datetime.today(), hora_obj)).total_seconds()
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

            duracion = str(timedelta(seconds=i))
            cronometro.markdown(f"### 🚶 Duración del desplazamiento: {duracion}")
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
                coleccion.update_one({"_id": evento["_id"]}, {"$set": {"fin": datetime.now(tz), "en_curso": False}})
                st.success("✅ Contención registrada.")
                st.rerun()

            duracion = str(timedelta(seconds=i))
            cronometro.markdown(f"### ⏱️ Tiempo resistido: {duracion}")
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
                coleccion.update_one({"_id": evento["_id"]}, {"$set": {"fin": datetime.now(tz), "en_curso": False}})
                st.success("✅ Pago registrado.")
                st.rerun()

            duracion = str(timedelta(seconds=i))
            cronometro.markdown(f"### ⏱️ Tiempo desde la intención de pago: {duracion}")
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

# === HISTORIAL ===
st.subheader(f"📜 Historial de {actividad}")
filtro = {"tipo": tipo_mongo, "en_curso": False}
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
            fila["Diferencia (min)"] = evento.get("diferencia_min", "")
        elif actividad == "Abstinencia":
            fila["Impulso"] = evento.get("subtipo", "desconocido")
        elif actividad == "Pagos":
            fila["Motivo"] = evento.get("subtipo", "desconocido")
            fila["Monto"] = evento.get("monto", 0)

        data.append(fila)

    st.dataframe(data, use_container_width=True)
else:
    st.info("No hay registros finalizados.")