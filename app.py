import streamlit as st
from openai import OpenAI
import json
import pandas as pd
from datetime import datetime
import plotly.express as px
import qrcode
from io import BytesIO

client = OpenAI(
    api_key=st.secrets["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)

MODELO = "openai/gpt-oss-120b"

# ====== CONTRASEÑA DEL ANFITRIÓN ======
HOST_PASSWORD = "admi1412"   # ← Cambia esta contraseña

SYSTEM_PROMPT = """
Eres un asistente muy empático, cálido y comprensivo, especializado en acompañar a estudiantes y trabajadores que están experimentando estrés.

Tu estilo de conversación debe ser:
- Cercano y humano (como un amigo de confianza que realmente escucha)
- Empático y validante (reconoces las emociones de la persona)
- Dinámico (haces preguntas de seguimiento naturales según lo que la persona te cuenta)
- Paciente (no apresuras el análisis)

Enfócate especialmente en explorar:
- Cómo se siente emocionalmente en este momento (ansiedad, tristeza, agotamiento, frustración, desmotivación, etc.)
- Nivel de energía y cansancio
- Si se siente solo/a o apoyado/a
- Qué situaciones le están generando más presión
- Cómo está afectando su día a día, sueño, concentración o relaciones
- Si ha pensado en renunciar al trabajo o abandonar la universidad

Haz una o dos preguntas a la vez. Escucha con atención y responde con comprensión antes de preguntar algo nuevo.

Cuando sientas que ya tienes una buena comprensión del estado emocional y de la situación de la persona, genera ÚNICAMENTE el siguiente JSON (sin texto adicional):

{
  "nivel_estres": "bajo | moderado | alto | muy_alto",
  "riesgo_renuncia_trabajo": "bajo | moderado | alto",
  "riesgo_abandono_universidad": "bajo | moderado | alto",
  "factores_principales": ["factor 1", "factor 2", "factor 3"],
  "recomendaciones": ["recomendación 1", "recomendación 2", "recomendación 3"],
  "urgencia": "ninguna | media | alta"
}

Sé muy cuidadoso. Nunca digas que es un diagnóstico médico. Si detectas alto sufrimiento emocional, recomienda con suavidad buscar apoyo profesional.
"""

st.set_page_config(page_title="Evaluador de Estrés", page_icon="🧠", layout="centered")
st.title("🧠 Evaluador de Estrés")
st.caption("Encuesta anónima • Sin fines de lucro • Solo con fines de análisis académico")

st.info("🔒 Esta evaluación es **100% anónima**. No se solicita nombre ni datos personales.")

# Inicializar
if "evaluaciones" not in st.session_state:
    st.session_state.evaluaciones = []

if "datos_iniciales" not in st.session_state:
    st.session_state.datos_iniciales = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "analisis_final" not in st.session_state:
    st.session_state.analisis_final = None

# ========== DATOS INICIALES ==========
if st.session_state.datos_iniciales is None:
    st.subheader("Datos generales (anónimos)")

    carrera = st.selectbox(
        "Carrera",
        ["Selecciona tu carrera", "Lic. Administración", "Lic. Derecho", "Lic. Comercio Internacional"]
    )

    cuatrimestre = st.selectbox(
        "Cuatrimestre actual",
        ["Selecciona el cuatrimestre", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    )

    if st.button("Comenzar evaluación"):
        if carrera != "Selecciona tu carrera" and cuatrimestre != "Selecciona el cuatrimestre":
            st.session_state.datos_iniciales = {
                "carrera": carrera,
                "cuatrimestre": cuatrimestre
            }
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": f"Hola 👋 Qué bueno que estás aquí. Sé que a veces no es fácil hablar de cómo nos sentimos. Estás en **{carrera}** (cuatrimestre {cuatrimestre}). Cuéntame, ¿cómo te has estado sintiendo últimamente con tus estudios o tu trabajo? Estoy aquí para escucharte."
                }
            ]
            st.rerun()
        else:
            st.warning("Por favor selecciona tu carrera y cuatrimestre.")

# ========== CONVERSACIÓN ==========
else:
    st.success(f"Carrera: **{st.session_state.datos_iniciales['carrera']}** | Cuatrimestre: **{st.session_state.datos_iniciales['cuatrimestre']}**")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Cuéntame cómo te sientes..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Escuchándote..."):
                try:
                    response = client.chat.completions.create(
                        model=MODELO,
                        messages=[{"role": "system", "content": SYSTEM_PROMPT}] +
                                 [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                        temperature=0.7,
                    )
                    respuesta = response.choices[0].message.content
                    st.markdown(respuesta)
                except Exception as e:
                    st.error(f"Error: {e}")
                    respuesta = "Lo siento, ocurrió un problema. ¿Puedes intentarlo de nuevo?"

        st.session_state.messages.append({"role": "assistant", "content": respuesta})

        if "{" in respuesta and "riesgo_renuncia_trabajo" in respuesta:
            try:
                inicio = respuesta.find("{")
                fin = respuesta.rfind("}") + 1
                analisis = json.loads(respuesta[inicio:fin])
                st.session_state.analisis_final = analisis

                evaluacion = {
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "carrera": st.session_state.datos_iniciales["carrera"],
                    "cuatrimestre": st.session_state.datos_iniciales["cuatrimestre"],
                    "nivel_estres": analisis.get("nivel_estres", ""),
                    "riesgo_renuncia_trabajo": analisis.get("riesgo_renuncia_trabajo", ""),
                    "riesgo_abandono_universidad": analisis.get("riesgo_abandono_universidad", ""),
                    "factores": " | ".join(analisis.get("factores_principales", []))
                }
                st.session_state.evaluaciones.append(evaluacion)
            except:
                pass

    # ========== RESULTADO ==========
    if st.session_state.analisis_final:
        st.divider()
        st.subheader("📊 Resultado de esta evaluación")

        a = st.session_state.analisis_final

        col1, col2, col3 = st.columns(3)
        col1.metric("Nivel de estrés", a.get("nivel_estres", "—").replace("_", " ").upper())
        col2.metric("Riesgo renuncia trabajo", a.get("riesgo_renuncia_trabajo", "—").upper())
        col3.metric("Riesgo abandono universidad", a.get("riesgo_abandono_universidad", "—").upper())

        if a.get("factores_principales"):
            st.markdown("**Factores principales detectados:**")
            for f in a["factores_principales"]:
                st.write(f"• {f}")

        if a.get("recomendaciones"):
            st.markdown("**Recomendaciones:**")
            for r in a["recomendaciones"]:
                st.write(f"• {r}")

        st.warning("""
        ⚠️ **Importante:**  
        Esta es una herramienta de orientación y **no constituye una valoración ni diagnóstico médico o psicológico**.
        """)

        st.markdown("""
        ### ¿Necesitas apoyo?
        Si te sientes abrumado, con mucha ansiedad o tienes pensamientos de abandonar, puedes contactar:

        - **Línea de la Vida (México)**: 800 911 2000  
        - **SAPTEL**: 55 5259-8121  
        - **Emergencias**: 911  
        - Psicología de tu universidad o un profesional de la salud mental  
        - Una persona de confianza

        No estás solo/a. Pedir ayuda es un acto de valentía.
        """)

        if a.get("urgencia") == "alta":
            st.error("Se recomienda buscar apoyo profesional lo antes posible.")

    if st.button("🔄 Empezar nueva evaluación"):
        st.session_state.datos_iniciales = None
        st.session_state.messages = []
        st.session_state.analisis_final = None
        st.rerun()

# ========== CÓDIGO QR ==========
with st.expander("📱 Compartir esta encuesta (Código QR)"):
    app_url = "https://evaluador-estres-20-avue9v2x4btmjimt97txof.streamlit.app/"   # ← Cambia por tu enlace real

    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(app_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    st.image(buffer.getvalue(), width=220)
    st.caption("Escanea para abrir la encuesta desde el celular")

# ========== ACCESO SOLO ANFITRIÓN ==========
st.divider()
st.subheader("🔐 Acceso anfitrión (solo resultados)")

password = st.text_input("Contraseña para ver resultados:", type="password")

if password == HOST_PASSWORD:
    st.success("Acceso concedido")

    if st.session_state.evaluaciones:
        df = pd.DataFrame(st.session_state.evaluaciones)

        st.write(f"**{len(df)}** evaluaciones recolectadas")
        st.dataframe(df, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.pie(df, names="riesgo_renuncia_trabajo", title="Riesgo de renuncia al trabajo")
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = px.pie(df, names="riesgo_abandono_universidad", title="Riesgo de abandono de estudios")
            st.plotly_chart(fig2, use_container_width=True)

        todos_factores = []
        for factores in df["factores"]:
            if factores:
                todos_factores.extend([f.strip() for f in factores.split("|")])

        if todos_factores:
            df_factores = pd.Series(todos_factores).value_counts().reset_index()
            df_factores.columns = ["Factor", "Cantidad"]
            fig3 = px.bar(df_factores, x="Factor", y="Cantidad", title="Factores que más influyen")
            st.plotly_chart(fig3, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Descargar todos los datos (CSV)",
            data=csv,
            file_name=f"estres_estudiantes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    else:
        st.info("Aún no hay evaluaciones recolectadas.")

elif password:
    st.error("Contraseña incorrecta")

st.markdown("---")
st.caption("Encuesta anónima • Sin fines de lucro • Esta herramienta no sustituye la atención de un profesional de la salud mental.")

