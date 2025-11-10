"""
Interfaz Streamlit para predicción de readmisión de pacientes diabéticos.
Consume la API de inferencia y muestra información del modelo.
"""
import streamlit as st
import requests
import json
from typing import Dict, Any

# Configuración
API_URL = "http://api:8000"

st.set_page_config(
    page_title="Diabetes Readmission Predictor",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 Predicción de Readmisión de Pacientes Diabéticos")
st.markdown("---")


@st.cache_data(ttl=60)
def get_model_info() -> Dict[str, Any]:
    """Obtiene información del modelo desde la API."""
    try:
        response = requests.get(f"{API_URL}/model/info", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error conectando con API: {e}")
        return {}


def predict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Realiza predicción llamando a la API."""
    try:
        response = requests.post(
            f"{API_URL}/predict",
            json=data,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error en predicción: {e}")
        return {}


# Sidebar: Información del modelo
with st.sidebar:
    st.header("📊 Información del Modelo")
    
    if st.button("🔄 Actualizar Info"):
        st.cache_data.clear()
    
    model_info = get_model_info()
    
    if model_info:
        st.success("✅ API Conectada")
        st.metric("Modelo", model_info.get("model_name", "N/A"))
        st.metric("Versión", model_info.get("model_version", "N/A"))
        st.metric("Stage", model_info.get("stage", "N/A"))
        st.info(f"MLflow URI: {model_info.get('mlflow_uri', 'N/A')}")
    else:
        st.error("❌ API No Disponible")
    
    st.markdown("---")
    st.markdown("""
    ### 📖 Acerca de
    Esta aplicación predice la probabilidad de readmisión hospitalaria 
    de pacientes diabéticos basándose en datos clínicos.
    
    **Clases de predicción:**
    - **NO**: No readmitido
    - **<30**: Readmitido en < 30 días
    - **>30**: Readmitido en > 30 días
    """)

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.header("🩺 Datos del Paciente")
    
    with st.form("prediction_form"):
        st.subheader("Información Demográfica")
        age_numeric = st.slider(
            "Edad del Paciente",
            min_value=0,
            max_value=100,
            value=55,
            help="Edad en años"
        )
        
        st.subheader("Información de Hospitalización")
        col_a, col_b = st.columns(2)
        
        with col_a:
            time_in_hospital = st.number_input(
                "Días en Hospital",
                min_value=1,
                max_value=14,
                value=3,
                help="Duración de la estadía (1-14 días)"
            )
            
            num_lab_procedures = st.number_input(
                "Procedimientos de Laboratorio",
                min_value=0,
                max_value=200,
                value=45,
                help="Número de pruebas de lab realizadas"
            )
            
            num_procedures = st.number_input(
                "Número de Procedimientos",
                min_value=0,
                max_value=10,
                value=1,
                help="Procedimientos realizados (excepto lab)"
            )
            
            num_medications = st.number_input(
                "Medicamentos Administrados",
                min_value=0,
                max_value=100,
                value=15,
                help="Cantidad de medicamentos distintos"
            )
        
        with col_b:
            number_outpatient = st.number_input(
                "Visitas Ambulatorias Previas",
                min_value=0,
                max_value=50,
                value=0,
                help="Visitas ambulatorias en el año anterior"
            )
            
            number_emergency = st.number_input(
                "Visitas de Emergencia Previas",
                min_value=0,
                max_value=50,
                value=0,
                help="Visitas de emergencia en el año anterior"
            )
            
            number_inpatient = st.number_input(
                "Hospitalizaciones Previas",
                min_value=0,
                max_value=50,
                value=0,
                help="Hospitalizaciones en el año anterior"
            )
            
            number_diagnoses = st.number_input(
                "Número de Diagnósticos",
                min_value=1,
                max_value=16,
                value=9,
                help="Cantidad de diagnósticos ingresados"
            )
        
        st.subheader("Resultados de Laboratorio")
        col_c, col_d = st.columns(2)
        
        with col_c:
            max_glu_serum = st.selectbox(
                "Nivel de Glucosa Sérica",
                options=["None", "Norm", ">200", ">300"],
                index=0,
                help="Resultado de prueba de glucosa sérica"
            )
            
            a1cresult = st.selectbox(
                "Resultado de A1c",
                options=["None", "Norm", ">7", ">8"],
                index=0,
                help="Resultado de prueba de hemoglobina A1c"
            )
        
        with col_d:
            change = st.selectbox(
                "Cambio en Medicación",
                options=["No", "Ch"],
                index=1,
                help="¿Se cambió la medicación durante la visita?"
            )
            
            diabetesmed = st.selectbox(
                "Medicación para Diabetes",
                options=["No", "Yes"],
                index=1,
                help="¿Se prescribió medicación para diabetes?"
            )
        
        num_diabetes_meds = st.slider(
            "Cantidad de Medicamentos para Diabetes",
            min_value=0,
            max_value=10,
            value=2,
            help="Número de medicamentos específicos para diabetes"
        )
        
        submitted = st.form_submit_button("🔮 Predecir Readmisión", use_container_width=True)

with col2:
    st.header("📋 Resultado")
    
    if submitted:
        # Mapear valores
        glu_map = {"None": 0, "Norm": 1, ">200": 2, ">300": 3}
        a1c_map = {"None": 0, "Norm": 1, ">7": 2, ">8": 3}
        
        # Preparar datos
        input_data = {
            "age_numeric": age_numeric,
            "time_in_hospital": time_in_hospital,
            "num_lab_procedures": num_lab_procedures,
            "num_procedures": num_procedures,
            "num_medications": num_medications,
            "number_outpatient": number_outpatient,
            "number_emergency": number_emergency,
            "number_inpatient": number_inpatient,
            "number_diagnoses": number_diagnoses,
            "max_glu_serum_encoded": glu_map[max_glu_serum],
            "a1cresult_encoded": a1c_map[a1cresult],
            "change_encoded": 1 if change == "Ch" else 0,
            "diabetesmed_encoded": 1 if diabetesmed == "Yes" else 0,
            "num_diabetes_meds": num_diabetes_meds
        }
        
        with st.spinner("Realizando predicción..."):
            result = predict(input_data)
        
        if result:
            prediction = result.get("prediction", "Unknown")
            
            # Mostrar resultado con color
            if prediction == "NO":
                st.success("### ✅ NO Readmisión")
                st.info("El paciente tiene baja probabilidad de ser readmitido.")
            elif prediction == "<30":
                st.error("### ⚠️ Readmisión < 30 días")
                st.warning("Alto riesgo de readmisión en menos de 30 días.")
            elif prediction == ">30":
                st.warning("### ⏰ Readmisión > 30 días")
                st.info("Riesgo moderado de readmisión después de 30 días.")
            else:
                st.info(f"### Resultado: {prediction}")
            
            st.markdown("---")
            
            # Información del modelo usado
            st.markdown("**🤖 Modelo Utilizado:**")
            st.code(f"{result.get('model_name', 'N/A')} v{result.get('model_version', 'N/A')}")
            
            # Mostrar JSON de respuesta
            with st.expander("📄 Ver respuesta completa (JSON)"):
                st.json(result)
    else:
        st.info("👈 Complete el formulario y presione 'Predecir Readmisión' para obtener resultados.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>🎓 Proyecto MLOps - Operaciones de Aprendizaje de Máquina</p>
    <p>Sistema integrado: Airflow + MLflow + FastAPI + Streamlit + Kubernetes</p>
</div>
""", unsafe_allow_html=True)
