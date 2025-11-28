"""
Streamlit Frontend - Interfaz de Usuario

Funcionalidades:
- Predicción individual de pacientes
- Predicción en batch (upload CSV)
- Visualización de explicabilidad SHAP
- Información del modelo en producción
- Estadísticas de predicciones
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List
import os
import time
import shap
import matplotlib.pyplot as plt
import numpy as np
import io
import base64

API_URL = os.getenv("API_URL", "http://api:8000")

st.set_page_config(
    page_title="MLOps Diabetes Prediction",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


def check_api_health() -> bool:
    """
    Verifica que la API esté disponible
    
    Returns:
        bool: True si API está disponible
    """
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def get_model_info() -> Dict:
    """
    Obtiene información del modelo en producción
    
    Returns:
        dict: Información del modelo
    """
    try:
        response = requests.get(f"{API_URL}/model-info", timeout=5)
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}


def predict_single(patient_data: Dict) -> Dict:
    """
    Hace predicción individual
    
    Args:
        patient_data: Datos del paciente
    
    Returns:
        dict: Resultado de predicción
    """
    try:
        response = requests.post(
            f"{API_URL}/predict",
            json={"patient": patient_data},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}


def predict_batch(df: pd.DataFrame) -> List[Dict]:
    """
    Hace predicción en batch
    
    Args:
        df: DataFrame con datos de múltiples pacientes
    
    Returns:
        list: Lista de predicciones
    """
    try:
        patients = df.to_dict('records')
        response = requests.post(
            f"{API_URL}/predict-batch",
            json={"patients": patients},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def get_shap_explanation(patient_data: Dict) -> Dict:
    """
    Obtiene explicación SHAP del modelo
    
    Args:
        patient_data: Datos del paciente
    
    Returns:
        dict: Explicación SHAP con valores y feature names
    """
    try:
        response = requests.post(
            f"{API_URL}/explain",
            json={"patient": patient_data},
            timeout=15
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}


def plot_shap_waterfall(shap_values: List[float], feature_names: List[str], base_value: float, prediction: float):
    """
    Crea gráfico waterfall de SHAP
    
    Args:
        shap_values: Valores SHAP
        feature_names: Nombres de features
        base_value: Valor base del modelo
        prediction: Predicción final
    """
    # Crear DataFrame con valores SHAP
    df = pd.DataFrame({
        'Feature': feature_names,
        'SHAP Value': shap_values
    })
    
    # Ordenar por valor absoluto
    df['abs_value'] = df['SHAP Value'].abs()
    df = df.sort_values('abs_value', ascending=False).head(15)
    
    # Crear gráfico de barras con Plotly
    fig = go.Figure()
    
    colors = ['red' if x < 0 else 'green' for x in df['SHAP Value']]
    
    fig.add_trace(go.Bar(
        y=df['Feature'],
        x=df['SHAP Value'],
        orientation='h',
        marker=dict(color=colors),
        text=[f"{v:.3f}" for v in df['SHAP Value']],
        textposition='auto'
    ))
    
    fig.update_layout(
        title=f"Top 15 Features - SHAP Explanation<br><sub>Base value: {base_value:.3f} → Prediction: {prediction:.3f}</sub>",
        xaxis_title="SHAP Value (impact on model output)",
        yaxis_title="Feature",
        height=600,
        showlegend=False
    )
    
    return fig


def plot_shap_force(shap_values: List[float], feature_names: List[str], base_value: float):
    """
    Crea gráfico tipo force plot simplificado
    
    Args:
        shap_values: Valores SHAP
        feature_names: Nombres de features
        base_value: Valor base
    """
    # Top features positivas y negativas
    df = pd.DataFrame({
        'Feature': feature_names,
        'SHAP Value': shap_values
    })
    
    positive = df[df['SHAP Value'] > 0].nlargest(10, 'SHAP Value')
    negative = df[df['SHAP Value'] < 0].nsmallest(10, 'SHAP Value')
    
    fig = go.Figure()
    
    # Features positivas (aumentan predicción)
    fig.add_trace(go.Bar(
        name='Increases Risk',
        y=positive['Feature'],
        x=positive['SHAP Value'],
        orientation='h',
        marker=dict(color='red'),
        text=[f"+{v:.3f}" for v in positive['SHAP Value']],
        textposition='auto'
    ))
    
    # Features negativas (disminuyen predicción)
    fig.add_trace(go.Bar(
        name='Decreases Risk',
        y=negative['Feature'],
        x=negative['SHAP Value'],
        orientation='h',
        marker=dict(color='green'),
        text=[f"{v:.3f}" for v in negative['SHAP Value']],
        textposition='auto'
    ))
    
    fig.update_layout(
        title=f"Feature Impact on Prediction<br><sub>Base value: {base_value:.3f}</sub>",
        xaxis_title="SHAP Value",
        yaxis_title="Feature",
        barmode='relative',
        height=500
    )
    
    return fig


st.markdown('<p class="main-header">🏥 MLOps Diabetes Readmission Prediction</p>', unsafe_allow_html=True)

with st.sidebar:
    st.header("ℹ️ Model Information")
    
    model_info = get_model_info()
    if model_info:
        st.success("✅ Model Loaded")
        st.metric("Model Name", model_info.get('model_name', 'N/A'))
        st.metric("Version", model_info.get('model_version', 'N/A'))
        st.metric("Stage", model_info.get('stage', 'N/A'))
    else:
        st.error("❌ Model Not Available")
    
    st.divider()
    
    st.header("📊 API Status")
    if check_api_health():
        st.success("✅ API Connected")
    else:
        st.error("❌ API Unavailable")
    
    st.divider()
    
    st.markdown("### About")
    st.markdown("""
    This application predicts hospital readmission risk for diabetic patients.
    
    **Model**: Dynamic loading from MLflow Production
    
    **Features**:
    - Single patient prediction
    - Batch predictions via CSV
    - Model explainability
    """)

tab1, tab2, tab3, tab4 = st.tabs(["🔍 Single Prediction", "📊 Batch Prediction", "🧠 SHAP Explainability", "📈 Analytics"])

with tab1:
    st.header("Individual Patient Prediction")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Patient Information")
        
        with st.form("patient_form"):
            col_a, col_b = st.columns(2)
            
            with col_a:
                age_numeric = st.number_input("Age", min_value=0, max_value=100, value=55)
                time_in_hospital = st.number_input("Days in Hospital", min_value=1, max_value=14, value=3)
                num_lab_procedures = st.number_input("Lab Procedures", min_value=0, value=45)
                num_procedures = st.number_input("Procedures", min_value=0, max_value=10, value=1)
                num_medications = st.number_input("Medications", min_value=0, value=15)
                number_outpatient = st.number_input("Outpatient Visits", min_value=0, value=0)
                number_emergency = st.number_input("Emergency Visits", min_value=0, value=0)
                number_inpatient = st.number_input("Inpatient Visits", min_value=0, value=0)
                number_diagnoses = st.number_input("Diagnoses", min_value=1, max_value=16, value=9)
                num_diabetes_meds = st.number_input("Diabetes Meds", min_value=0, value=2)
                gender_encoded = st.selectbox("Gender", [0, 1], format_func=lambda x: "Female" if x == 0 else "Male")
            
            with col_b:
                max_glu_serum_encoded = st.selectbox("Max Glucose", [0, 1, 2, 3], format_func=lambda x: ["None", "Norm", ">200", ">300"][x])
                a1cresult_encoded = st.selectbox("A1C Result", [0, 1, 2, 3], format_func=lambda x: ["None", "Norm", ">7", ">8"][x])
                change_encoded = st.selectbox("Change in Meds", [0, 1], format_func=lambda x: "No" if x == 0 else "Yes")
                diabetesmed_encoded = st.selectbox("Diabetes Med", [0, 1], format_func=lambda x: "No" if x == 0 else "Yes")
                race_encoded = st.number_input("Race", min_value=0, max_value=5, value=2)
                admission_type_encoded = st.number_input("Admission Type", min_value=0, max_value=7, value=1)
                discharge_disposition_encoded = st.number_input("Discharge Disposition", min_value=0, max_value=28, value=1)
                admission_source_encoded = st.number_input("Admission Source", min_value=0, max_value=25, value=7)
                payer_code_encoded = st.number_input("Payer Code", min_value=0, max_value=22, value=5)
                medical_specialty_encoded = st.number_input("Medical Specialty", min_value=0, max_value=83, value=12)
                diag_1_encoded = st.number_input("Primary Diagnosis", min_value=0, value=250)
            
            predict_button = st.form_submit_button("🔮 Predict", type="primary")
    
    with col2:
        st.subheader("Prediction Result")
        
        if predict_button:
            patient_data = {
                "age_numeric": age_numeric,
                "time_in_hospital": time_in_hospital,
                "num_lab_procedures": num_lab_procedures,
                "num_procedures": num_procedures,
                "num_medications": num_medications,
                "number_outpatient": number_outpatient,
                "number_emergency": number_emergency,
                "number_inpatient": number_inpatient,
                "number_diagnoses": number_diagnoses,
                "max_glu_serum_encoded": max_glu_serum_encoded,
                "a1cresult_encoded": a1cresult_encoded,
                "change_encoded": change_encoded,
                "diabetesmed_encoded": diabetesmed_encoded,
                "num_diabetes_meds": num_diabetes_meds,
                "gender_encoded": gender_encoded,
                "race_encoded": race_encoded,
                "admission_type_encoded": admission_type_encoded,
                "discharge_disposition_encoded": discharge_disposition_encoded,
                "admission_source_encoded": admission_source_encoded,
                "payer_code_encoded": payer_code_encoded,
                "medical_specialty_encoded": medical_specialty_encoded,
                "diag_1_encoded": diag_1_encoded
            }
            
            with st.spinner("Making prediction..."):
                result = predict_single(patient_data)
            
            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                prediction = result.get('prediction', 0)
                readmission_map = {0: "NO", 1: "<30 days", 2: ">30 days"}
                pred_label = readmission_map.get(prediction, "Unknown")
                
                if prediction == 0:
                    st.success(f"✅ Readmission Risk: **{pred_label}**")
                elif prediction == 1:
                    st.warning(f"⚠️ Readmission Risk: **{pred_label}**")
                else:
                    st.info(f"ℹ️ Readmission Risk: **{pred_label}**")
                
                st.metric("Model Version", result.get('model_version', 'N/A'))

with tab2:
    st.header("Batch Prediction")
    
    st.markdown("""
    Upload a CSV file with patient data to get predictions for multiple patients.
    
    **Required columns**: age_numeric, time_in_hospital, num_lab_procedures, num_procedures, num_medications, 
    number_outpatient, number_emergency, number_inpatient, number_diagnoses, max_glu_serum_encoded, 
    a1cresult_encoded, change_encoded, diabetesmed_encoded, num_diabetes_meds, gender_encoded, race_encoded, 
    admission_type_encoded, discharge_disposition_encoded, admission_source_encoded, payer_code_encoded, 
    medical_specialty_encoded, diag_1_encoded
    """)
    
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write("Preview of uploaded data:")
        st.dataframe(df.head())
        
        if st.button("🔮 Predict Batch"):
            with st.spinner("Making predictions..."):
                result = predict_batch(df)
            
            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                predictions = result.get('predictions', [])
                results_df = pd.DataFrame(predictions)
                st.success(f"✅ Predictions completed: {len(predictions)} patients")
                st.dataframe(results_df)
                
                csv = results_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Results",
                    data=csv,
                    file_name="predictions.csv",
                    mime="text/csv"
                )

with tab3:
    st.header("🧠 SHAP Model Explainability")
    
    st.markdown("""
    **SHAP (SHapley Additive exPlanations)** explains individual predictions by computing the contribution 
    of each feature to the model's output.
    
    - **Positive SHAP values** (red): Feature increases readmission risk
    - **Negative SHAP values** (green): Feature decreases readmission risk
    """)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Patient Data")
        
        with st.form("shap_form"):
            col_a, col_b = st.columns(2)
            
            with col_a:
                age_shap = st.number_input("Age", min_value=0, max_value=100, value=65, key="age_shap")
                time_hospital_shap = st.number_input("Days in Hospital", min_value=1, max_value=14, value=5, key="time_shap")
                num_lab_shap = st.number_input("Lab Procedures", min_value=0, value=50, key="lab_shap")
                num_proc_shap = st.number_input("Procedures", min_value=0, max_value=10, value=2, key="proc_shap")
                num_meds_shap = st.number_input("Medications", min_value=0, value=20, key="meds_shap")
                outpatient_shap = st.number_input("Outpatient Visits", min_value=0, value=1, key="out_shap")
                emergency_shap = st.number_input("Emergency Visits", min_value=0, value=0, key="emerg_shap")
                inpatient_shap = st.number_input("Inpatient Visits", min_value=0, value=1, key="inp_shap")
                diagnoses_shap = st.number_input("Diagnoses", min_value=1, max_value=16, value=9, key="diag_shap")
                diabetes_meds_shap = st.number_input("Diabetes Meds", min_value=0, value=3, key="dmed_shap")
                gender_shap = st.selectbox("Gender", [0, 1], format_func=lambda x: "Female" if x == 0 else "Male", key="gender_shap")
            
            with col_b:
                glu_shap = st.selectbox("Max Glucose", [0, 1, 2, 3], format_func=lambda x: ["None", "Norm", ">200", ">300"][x], key="glu_shap")
                a1c_shap = st.selectbox("A1C Result", [0, 1, 2, 3], format_func=lambda x: ["None", "Norm", ">7", ">8"][x], key="a1c_shap")
                change_shap = st.selectbox("Change in Meds", [0, 1], format_func=lambda x: "No" if x == 0 else "Yes", key="change_shap")
                diabetesmed_shap = st.selectbox("Diabetes Med", [0, 1], format_func=lambda x: "No" if x == 0 else "Yes", key="dmed2_shap")
                race_shap = st.number_input("Race", min_value=0, max_value=5, value=2, key="race_shap")
                admission_shap = st.number_input("Admission Type", min_value=0, max_value=7, value=1, key="adm_shap")
                discharge_shap = st.number_input("Discharge Disposition", min_value=0, max_value=28, value=1, key="dis_shap")
                source_shap = st.number_input("Admission Source", min_value=0, max_value=25, value=7, key="src_shap")
                payer_shap = st.number_input("Payer Code", min_value=0, max_value=22, value=5, key="pay_shap")
                specialty_shap = st.number_input("Medical Specialty", min_value=0, max_value=83, value=12, key="spec_shap")
                diag1_shap = st.number_input("Primary Diagnosis", min_value=0, value=250, key="diag1_shap")
            
            explain_button = st.form_submit_button("🔍 Explain Prediction", type="primary")
    
    with col2:
        st.subheader("SHAP Explanation")
        
        if explain_button:
            patient_data_shap = {
                "age_numeric": age_shap,
                "time_in_hospital": time_hospital_shap,
                "num_lab_procedures": num_lab_shap,
                "num_procedures": num_proc_shap,
                "num_medications": num_meds_shap,
                "number_outpatient": outpatient_shap,
                "number_emergency": emergency_shap,
                "number_inpatient": inpatient_shap,
                "number_diagnoses": diagnoses_shap,
                "max_glu_serum_encoded": glu_shap,
                "a1cresult_encoded": a1c_shap,
                "change_encoded": change_shap,
                "diabetesmed_encoded": diabetesmed_shap,
                "num_diabetes_meds": diabetes_meds_shap,
                "gender_encoded": gender_shap,
                "race_encoded": race_shap,
                "admission_type_encoded": admission_shap,
                "discharge_disposition_encoded": discharge_shap,
                "admission_source_encoded": source_shap,
                "payer_code_encoded": payer_shap,
                "medical_specialty_encoded": specialty_shap,
                "diag_1_encoded": diag1_shap
            }
            
            with st.spinner("Calculating SHAP values..."):
                # Obtener predicción primero
                pred_result = predict_single(patient_data_shap)
                
                if "error" not in pred_result:
                    prediction = pred_result.get('prediction', 0)
                    readmission_map = {0: "NO", 1: "<30 days", 2: ">30 days"}
                    pred_label = readmission_map.get(prediction, "Unknown")
                    
                    if prediction == 0:
                        st.success(f"✅ Readmission Risk: **{pred_label}**")
                    elif prediction == 1:
                        st.warning(f"⚠️ Readmission Risk: **{pred_label}**")
                    else:
                        st.info(f"ℹ️ Readmission Risk: **{pred_label}**")
                    
                    # Obtener explicación SHAP
                    shap_result = get_shap_explanation(patient_data_shap)
                    
                    if "error" not in shap_result:
                        shap_values = shap_result.get('shap_values', [])
                        feature_names = shap_result.get('feature_names', [])
                        base_value = shap_result.get('base_value', 0.0)
                        prediction_value = shap_result.get('prediction', 0.0)
                        
                        if shap_values and feature_names:
                            st.divider()
                            st.subheader("Feature Importance")
                            
                            # Gráfico waterfall
                            fig_waterfall = plot_shap_waterfall(shap_values, feature_names, base_value, prediction_value)
                            st.plotly_chart(fig_waterfall, use_container_width=True)
                            
                            st.divider()
                            st.subheader("Impact Direction")
                            
                            # Gráfico force
                            fig_force = plot_shap_force(shap_values, feature_names, base_value)
                            st.plotly_chart(fig_force, use_container_width=True)
                            
                            # Tabla de valores
                            st.divider()
                            st.subheader("SHAP Values Table")
                            shap_df = pd.DataFrame({
                                'Feature': feature_names,
                                'SHAP Value': shap_values,
                                'Absolute Impact': [abs(v) for v in shap_values]
                            }).sort_values('Absolute Impact', ascending=False)
                            st.dataframe(shap_df, use_container_width=True)
                        else:
                            st.warning("⚠️ SHAP values not available")
                    else:
                        st.error(f"❌ SHAP Error: {shap_result['error']}")
                else:
                    st.error(f"❌ Prediction Error: {pred_result['error']}")

with tab4:
    st.header("Model Analytics")
    
    st.info("Analytics dashboard coming soon...")
    
    st.markdown("""
    **Future Features**:
    - Prediction statistics
    - Feature importance visualization
    - Model performance metrics
    - Prediction distribution
    """)# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; padding: 2rem;'>
    <p>MLOps Project - Diabetes Readmission Prediction System</p>
    <p>Powered by MLflow, FastAPI, and Streamlit</p>
</div>
""", unsafe_allow_html=True)
