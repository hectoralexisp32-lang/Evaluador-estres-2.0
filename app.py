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
SYSTEM_PROMPT = """
Eres un asistente empático especializado en detectar estrés relacionado con trabajo y estudios universitarios.

Mantén una conversación natural. Cuando tengas suficiente información, responde ÚNICAMENTE con este JSON:

{
  "nivel_estres": "bajo | moderado | alto | muy_alto",
  "riesgo_renuncia_trabajo": "bajo | moderado | alto",
  "riesgo_abandono_universidad": "bajo | moderado | alto",
  "factores_principales": ["factor 1", "factor 2", "factor 3"]
}

Los factores deben ser cortos y claros. No incluyas recomendaciones ni texto adicional.
"""

st.set_page_config(page_title="Evaluador de Estrés", page_icon="🧠", layout="centered")
st.title("🧠 Evaluador de Estrés")
st.caption("Encuesta anónima • Sin fines de lucro • Solo con fines de análisis académico")

# Aviso de anonimato
st.info("🔒 Esta evaluación es **100% anónima**. No se solicita nombre, número de control ni ningún dato personal. Los resultados se usan únicamente para análisis estadístico.")

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
                    "content": f"Hola 👋 Gracias por participar. Estás en **{carrera}** (cuatrimestre {cuatrimestre}). ¿Cómo te has sentido últimamente con respecto a tus estudios o trabajo?"
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
            with st.spinner("Analizando..."):
                try:
                    response = client.chat.completions.create(
                        model=MODELO,
                        messages=[{"role": "system", "content": SYSTEM_PROMPT}] +
                                 [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                        temperature=0.6,
                    )
                    respuesta = response.choices[0].message.content
                    st.markdown(respuesta)
                except Exception as e:
                    st.error(f"Error: {e}")
                    respuesta = "Lo siento, ocurrió un problema. Intenta de nuevo."

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

    # Resultado individual
    if st.session_state.analisis_final:
        st.divider()
        st.subheader("📊 Resultado de esta evaluación")

        a = st.session_state.analisis_final

        col1, col2, col3 = st.columns(3)
        col1.metric("Nivel de estrés", a.get("nivel_estres", "—").replace("_", " ").upper())
        col2.metric("Riesgo renuncia trabajo", a.get("riesgo_renuncia_trabajo", "—").upper())
        col3.metric("Riesgo abandono universidad", a.get("riesgo_abandono_universidad", "—").upper())

        if a.get("factores_principales"):
            st.markdown("**Factores principales:**")
            for f in a["factores_principales"]:
                st.write(f"• {f}")

    if st.button("🔄 Empezar nueva evaluación"):
        st.session_state.datos_iniciales = None
        st.session_state.messages = []
        st.session_state.analisis_final = None
        st.rerun()

# ========== CÓDIGO QR ==========
with st.expander("📱 Compartir esta encuesta (Código QR)"):
    # Reemplaza esta URL por la real de tu app cuando la despliegues
    app_url = "https://tu-app.streamlit.app"   # ← cámbiala después

    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(app_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    st.image(buffer.getvalue(), width=220)
    st.caption("Escanea para abrir la encuesta desde el celular")

# ========== DATOS Y GRÁFICAS ==========
st.divider()
st.subheader("📈 Análisis de datos recolectados")

if st.session_state.evaluaciones:
    df = pd.DataFrame(st.session_state.evaluaciones)

    st.write(f"**{len(df)}** evaluaciones recolectadas")
    st.dataframe(df, use_container_width=True)

    # Gráficas
    col1, col2 = st.columns(2)

    with col1:
        fig1 = px.pie(df, names="riesgo_renuncia_trabajo", title="Riesgo de renuncia al trabajo")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = px.pie(df, names="riesgo_abandono_universidad", title="Riesgo de abandono de estudios")
        st.plotly_chart(fig2, use_container_width=True)

    # Factores más comunes
    todos_factores = []
    for factores in df["factores"]:
        if factores:
            todos_factores.extend([f.strip() for f in factores.split("|")])

    if todos_factores:
        df_factores = pd.Series(todos_factores).value_counts().reset_index()
        df_factores.columns = ["Factor", "Cantidad"]
        fig3 = px.bar(df_factores, x="Factor", y="Cantidad", title="Factores que más influyen")
        st.plotly_chart(fig3, use_container_width=True)

    # Gráfica por carrera
    fig4 = px.histogram(df, x="carrera", color="riesgo_abandono_universidad",
                        title="Riesgo de abandono por carrera", barmode="group")
    st.plotly_chart(fig4, use_container_width=True)

    # Descarga
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Descargar todos los datos (CSV)",
        data=csv,
        file_name=f"estres_estudiantes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )
else:
    st.info("Aún no hay evaluaciones. Realiza al menos una para ver las gráficas.")

st.markdown("---")
st.caption("Encuesta anónima • Sin fines de lucro • Uso exclusivo para análisis académico")

