"""
Streamlit Frontend - Predicción de Precios Inmobiliarios

Características:
- Predicción individual y batch
- Historial de modelos entrenados con métricas
- Explicabilidad con SHAP del modelo final
- Visualización de métricas y performance
- Conexión con FastAPI para inferencia
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import json

# Configuración
API_URL = os.getenv("API_URL", "http://api:8000")
MLFLOW_URL = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")

st.set_page_config(
    page_title="MLOps Realtor - Predicción de Precios",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A8A;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #3B82F6;
        margin-top: 1rem;
    }
    .metric-card {
        background-color: #F3F4F6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .prediction-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 1rem;
        text-align: center;
        font-size: 2rem;
        font-weight: bold;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #EFF6FF;
        border-left: 4px solid #3B82F6;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.25rem;
    }
    .warning-box {
        background-color: #FEF3C7;
        border-left: 4px solid #F59E0B;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)


def check_api_health():
    """Verifica estado de la API"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.json() if response.status_code == 200 else None
    except:
        return None


def get_model_info():
    """Obtiene información del modelo actual"""
    try:
        response = requests.get(f"{API_URL}/model-info", timeout=5)
        return response.json() if response.status_code == 200 else None
    except:
        return None


def get_models_history():
    """Obtiene historial de modelos"""
    try:
        response = requests.get(f"{API_URL}/models/history", timeout=10)
        return response.json() if response.status_code == 200 else None
    except:
        return None


def get_inference_stats():
    """Obtiene estadísticas de inferencias"""
    try:
        response = requests.get(f"{API_URL}/inference-stats", timeout=5)
        return response.json() if response.status_code == 200 else None
    except:
        return None


def predict_single(property_data):
    """Realiza predicción individual"""
    try:
        response = requests.post(
            f"{API_URL}/predict",
            json={"property": property_data},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.json().get("detail", "Unknown error")}
    except Exception as e:
        return {"error": str(e)}


def explain_prediction(property_data):
    """Obtiene explicación SHAP de una predicción"""
    try:
        response = requests.post(
            f"{API_URL}/explain",
            json={"property": property_data},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.json().get("detail", "Unknown error")}
    except Exception as e:
        return {"error": str(e)}


# Sidebar - Navegación
st.sidebar.markdown("# 🏠 MLOps Realtor")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navegación",
    ["🎯 Predicción", "📊 Historial de Modelos", "🔍 Explicabilidad (SHAP)", "📈 Estadísticas"]
)

st.sidebar.markdown("---")

# Estado de la API
health = check_api_health()
if health:
    if health.get("model_loaded"):
        st.sidebar.success("✅ API Conectada")
        model_info = get_model_info()
        if model_info:
            st.sidebar.info(f"""
**Modelo Activo:**
- Nombre: {model_info['model_name']}
- Versión: {model_info['model_version']}
- Stage: {model_info['model_stage']}
            """)
    else:
        st.sidebar.warning("⚠️ API conectada pero sin modelo")
else:
    st.sidebar.error("❌ API no disponible")

st.sidebar.markdown("---")
st.sidebar.markdown(f"**MLflow:** [{MLFLOW_URL}]({MLFLOW_URL})")


# ==================== PÁGINA: PREDICCIÓN ====================
if menu == "🎯 Predicción":
    st.markdown('<div class="main-header">🏠 Predicción de Precios Inmobiliarios</div>', unsafe_allow_html=True)
    
    if not health or not health.get("model_loaded"):
        st.markdown('<div class="warning-box">⚠️ El modelo no está disponible. Verifica que la API esté funcionando correctamente.</div>', unsafe_allow_html=True)
        st.stop()
    
    st.markdown('<div class="info-box">📋 Ingrese los datos de la propiedad para obtener una predicción de precio.</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🏢 Información General")
        brokered_by = st.text_input("Agencia/Corredor", "Century 21", help="Nombre de la agencia inmobiliaria")
        status = st.selectbox("Estado", ["for_sale", "ready_to_build"], help="Estado actual de la propiedad")
        street = st.text_input("Dirección", "123 Main St", help="Dirección de la calle")
        city = st.text_input("Ciudad", "Miami")
        state = st.text_input("Estado", "Florida")
        zip_code = st.text_input("Código Postal", "33101")
    
    with col2:
        st.markdown("### 📐 Características")
        bed = st.number_input("Habitaciones", min_value=0, max_value=20, value=3, help="Número de habitaciones")
        bath = st.number_input("Baños", min_value=0.0, max_value=10.0, value=2.0, step=0.5, help="Número de baños")
        house_size = st.number_input("Tamaño Casa (sq ft)", min_value=0, value=1500, step=100, help="Tamaño en pies cuadrados")
        acre_lot = st.number_input("Tamaño Terreno (acres)", min_value=0.0, value=0.25, step=0.05, help="Tamaño del terreno en acres")
    
    with col3:
        st.markdown("### 📅 Historial")
        prev_sold_date = st.date_input("Fecha Venta Anterior", value=None, help="Última fecha de venta (opcional)")
        
        st.markdown("### 💡 Acción")
        predict_button = st.button("🎯 Predecir Precio", type="primary", use_container_width=True)
        show_explanation = st.checkbox("Mostrar explicación SHAP", value=False)
    
    # Realizar predicción
    if predict_button:
        property_data = {
            "brokered_by": brokered_by,
            "status": status,
            "bed": bed,
            "bath": bath,
            "acre_lot": acre_lot,
            "street": street,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "house_size": house_size,
            "prev_sold_date": prev_sold_date.strftime("%Y-%m-%d") if prev_sold_date else None
        }
        
        with st.spinner("🔮 Analizando propiedad..."):
            result = predict_single(property_data)
        
        if "error" in result:
            st.error(f"❌ Error en la predicción: {result['error']}")
        else:
            # Mostrar predicción
            st.markdown('<div class="prediction-box">', unsafe_allow_html=True)
            st.markdown(f"Precio Predicho: ${result['predicted_price']:,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Metadata
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Modelo", result['model_name'])
            col_b.metric("Versión", result['model_version'])
            col_c.metric("Stage", result['model_stage'])
            
            # Mostrar explicación si se solicita
            if show_explanation:
                st.markdown("---")
                st.markdown('<div class="sub-header">🔍 Explicación SHAP</div>', unsafe_allow_html=True)
                
                with st.spinner("Calculando valores SHAP..."):
                    explanation = explain_prediction(property_data)
                
                if "error" in explanation:
                    st.warning(f"⚠️ No se pudo calcular SHAP: {explanation.get('message', explanation['error'])}")
                else:
                    if "shap_values" in explanation:
                        shap_df = pd.DataFrame(explanation['shap_values'])
                        
                        # Gráfico de barras SHAP
                        fig = px.bar(
                            shap_df.head(10),
                            x='value',
                            y='feature',
                            orientation='h',
                            title='Top 10 Features - Impacto en la Predicción',
                            labels={'value': 'Impacto SHAP', 'feature': 'Característica'},
                            color='value',
                            color_continuous_scale='RdBu_r'
                        )
                        fig.update_layout(height=500)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Tabla detallada
                        st.markdown("**Valores Detallados:**")
                        st.dataframe(shap_df, use_container_width=True)
                    else:
                        st.info(explanation.get('message', 'SHAP no disponible para este tipo de modelo'))


# ==================== PÁGINA: HISTORIAL DE MODELOS ====================
elif menu == "📊 Historial de Modelos":
    st.markdown('<div class="main-header">📊 Historial de Modelos Entrenados</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="info-box">📜 Aquí puedes ver todos los modelos entrenados, sus métricas y etapas de despliegue.</div>', unsafe_allow_html=True)
    
    with st.spinner("Cargando historial de modelos..."):
        history = get_models_history()
    
    if not history:
        st.error("❌ No se pudo obtener el historial de modelos")
        st.stop()
    
    st.markdown(f"### Total de versiones: **{history['total_versions']}**")
    
    if history['total_versions'] == 0:
        st.warning("⚠️ No hay modelos registrados aún. Ejecuta el DAG de entrenamiento en Airflow.")
        st.stop()
    
    # Métricas de resumen
    models = history['history']
    production_models = [m for m in models if m['stage'] == 'Production']
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Modelos", history['total_versions'])
    col2.metric("En Producción", len(production_models))
    col3.metric("Última Versión", models[0]['version'] if models else "N/A")
    col4.metric("Stage Actual", models[0]['stage'] if models else "N/A")
    
    st.markdown("---")
    
    # Tabla de modelos
    st.markdown('<div class="sub-header">📋 Tabla de Modelos</div>', unsafe_allow_html=True)
    
    models_df = pd.DataFrame([
        {
            "Versión": m['version'],
            "Stage": m['stage'],
            "RMSE": f"{m['metrics'].get('rmse', 0):.2f}" if m['metrics'].get('rmse') else "N/A",
            "MAE": f"{m['metrics'].get('mae', 0):.2f}" if m['metrics'].get('mae') else "N/A",
            "R²": f"{m['metrics'].get('r2', 0):.4f}" if m['metrics'].get('r2') else "N/A",
            "MAPE": f"{m['metrics'].get('mape', 0):.2f}%" if m['metrics'].get('mape') else "N/A",
            "Fecha Creación": datetime.fromtimestamp(m['creation_timestamp'] / 1000).strftime("%Y-%m-%d %H:%M"),
            "Run ID": m['run_id'][:8] + "..."
        }
        for m in models
    ])
    
    # Colorear filas según stage
    def highlight_production(row):
        if row['Stage'] == 'Production':
            return ['background-color: #D1FAE5'] * len(row)
        elif row['Stage'] == 'Staging':
            return ['background-color: #FEF3C7'] * len(row)
        else:
            return [''] * len(row)
    
    st.dataframe(
        models_df.style.apply(highlight_production, axis=1),
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    
    # Gráficos de evolución de métricas
    st.markdown('<div class="sub-header">📈 Evolución de Métricas</div>', unsafe_allow_html=True)
    
    # Preparar datos para gráficos
    metrics_data = []
    for m in reversed(models):  # Orden cronológico
        if m['metrics'].get('rmse') is not None:
            metrics_data.append({
                'Versión': f"v{m['version']}",
                'RMSE': m['metrics'].get('rmse', 0),
                'MAE': m['metrics'].get('mae', 0),
                'R²': m['metrics'].get('r2', 0),
                'MAPE': m['metrics'].get('mape', 0),
                'Stage': m['stage']
            })
    
    if metrics_data:
        metrics_df = pd.DataFrame(metrics_data)
        
            col_a, col_b = st.columns(2)
            
            with col_a:
            # RMSE
            fig_rmse = px.line(
                metrics_df,
                x='Versión',
                y='RMSE',
                markers=True,
                title='Evolución RMSE (menor es mejor)',
                color='Stage',
                color_discrete_map={'Production': '#10B981', 'Staging': '#F59E0B', 'None': '#6B7280'}
            )
            fig_rmse.update_layout(height=400)
            st.plotly_chart(fig_rmse, use_container_width=True)
            
            # R²
            fig_r2 = px.line(
                metrics_df,
                x='Versión',
                y='R²',
                markers=True,
                title='Evolución R² (mayor es mejor)',
                color='Stage',
                color_discrete_map={'Production': '#10B981', 'Staging': '#F59E0B', 'None': '#6B7280'}
            )
            fig_r2.update_layout(height=400)
            st.plotly_chart(fig_r2, use_container_width=True)
        
        with col_b:
            # MAE
            fig_mae = px.line(
                metrics_df,
                x='Versión',
                y='MAE',
                markers=True,
                title='Evolución MAE (menor es mejor)',
                color='Stage',
                color_discrete_map={'Production': '#10B981', 'Staging': '#F59E0B', 'None': '#6B7280'}
            )
            fig_mae.update_layout(height=400)
            st.plotly_chart(fig_mae, use_container_width=True)
            
            # MAPE
            fig_mape = px.line(
                metrics_df,
                x='Versión',
                y='MAPE',
                markers=True,
                title='Evolución MAPE % (menor es mejor)',
                color='Stage',
                color_discrete_map={'Production': '#10B981', 'Staging': '#F59E0B', 'None': '#6B7280'}
            )
            fig_mape.update_layout(height=400)
            st.plotly_chart(fig_mape, use_container_width=True)
    
    # Comparación de modelos
    st.markdown("---")
    st.markdown('<div class="sub-header">⚖️ Comparación de Modelos</div>', unsafe_allow_html=True)
    
    if len(metrics_data) >= 2:
        col_x, col_y = st.columns(2)
        
        with col_x:
            version_a = st.selectbox("Modelo A", [m['Versión'] for m in metrics_data], index=0)
        with col_y:
            version_b = st.selectbox("Modelo B", [m['Versión'] for m in metrics_data], index=min(1, len(metrics_data)-1))
        
        model_a = next(m for m in metrics_data if m['Versión'] == version_a)
        model_b = next(m for m in metrics_data if m['Versión'] == version_b)
        
        comparison_df = pd.DataFrame({
            'Métrica': ['RMSE', 'MAE', 'R²', 'MAPE'],
            version_a: [model_a['RMSE'], model_a['MAE'], model_a['R²'], model_a['MAPE']],
            version_b: [model_b['RMSE'], model_b['MAE'], model_b['R²'], model_b['MAPE']],
            'Diferencia': [
                model_a['RMSE'] - model_b['RMSE'],
                model_a['MAE'] - model_b['MAE'],
                model_a['R²'] - model_b['R²'],
                model_a['MAPE'] - model_b['MAPE']
            ]
        })
        
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(name=version_a, x=comparison_df['Métrica'], y=comparison_df[version_a]))
        fig_comp.add_trace(go.Bar(name=version_b, x=comparison_df['Métrica'], y=comparison_df[version_b]))
        fig_comp.update_layout(barmode='group', title='Comparación de Métricas', height=400)
        st.plotly_chart(fig_comp, use_container_width=True)


# ==================== PÁGINA: EXPLICABILIDAD SHAP ====================
elif menu == "🔍 Explicabilidad (SHAP)":
    st.markdown('<div class="main-header">🔍 Explicabilidad con SHAP</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="info-box">🧠 SHAP (SHapley Additive exPlanations) ayuda a entender cómo cada característica contribuye a la predicción del modelo.</div>', unsafe_allow_html=True)
    
    if not health or not health.get("model_loaded"):
        st.warning("⚠️ El modelo no está disponible.")
        st.stop()
    
    st.markdown("### 🎯 Realizar Predicción y Obtener Explicación")
    
    # Formulario simplificado
    col1, col2 = st.columns(2)
    
    with col1:
        bed = st.number_input("Habitaciones", 0, 20, 3)
        bath = st.number_input("Baños", 0.0, 10.0, 2.0, 0.5)
        house_size = st.number_input("Tamaño Casa (sq ft)", 0, 10000, 1500, 100)
        acre_lot = st.number_input("Tamaño Terreno (acres)", 0.0, 10.0, 0.25, 0.05)
        city = st.text_input("Ciudad", "Miami")
    
    with col2:
        state = st.text_input("Estado", "Florida")
        zip_code = st.text_input("Código Postal", "33101")
        status = st.selectbox("Estado Propiedad", ["for_sale", "ready_to_build"])
        brokered_by = st.text_input("Agencia", "Century 21")
        street = st.text_input("Calle", "123 Main St")
    
    if st.button("🔍 Analizar con SHAP", type="primary"):
        property_data = {
            "brokered_by": brokered_by,
            "status": status,
            "bed": bed,
            "bath": bath,
            "acre_lot": acre_lot,
            "street": street,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "house_size": house_size,
            "prev_sold_date": None
        }
        
        with st.spinner("🔮 Calculando explicación SHAP..."):
            explanation = explain_prediction(property_data)
        
        if "error" in explanation:
            st.error(f"❌ Error: {explanation.get('message', explanation['error'])}")
        else:
            # Predicción
            st.markdown('<div class="prediction-box">', unsafe_allow_html=True)
            st.markdown(f"Precio Predicho: ${explanation['predicted_price']:,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if "shap_values" in explanation:
                st.markdown("---")
                st.markdown('<div class="sub-header">📊 Valores SHAP</div>', unsafe_allow_html=True)
                
                shap_df = pd.DataFrame(explanation['shap_values'])
                
                # Valor base
                st.info(f"📍 **Valor Base del Modelo:** ${explanation.get('base_value', 0):,.2f}")
                
                # Gráfico principal SHAP
                fig = px.bar(
                    shap_df.head(15),
                    x='value',
                    y='feature',
                    orientation='h',
                    title='Impacto de Características en la Predicción (SHAP Values)',
                    labels={'value': 'Impacto SHAP', 'feature': 'Característica'},
                    color='value',
                    color_continuous_scale='RdBu_r',
                    text='value'
                )
                fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                fig.update_layout(height=600)
                st.plotly_chart(fig, use_container_width=True)
                
                # Explicación
                st.markdown("### 💡 Interpretación")
                st.markdown("""
                - **Valores positivos (rojos):** Aumentan el precio predicho
                - **Valores negativos (azules):** Disminuyen el precio predicho
                - **Magnitud:** Indica el impacto relativo de cada característica
                """)
                
                # Top features
                st.markdown("### 🏆 Top 5 Características Más Influyentes")
                top_5 = shap_df.head(5)
                for idx, row in top_5.iterrows():
                    impact = "aumenta" if row['value'] > 0 else "disminuye"
                    st.markdown(f"**{idx+1}. {row['feature']}:** {impact} el precio en **${abs(row['value']):,.2f}**")
                
                # Tabla completa
                st.markdown("---")
                st.markdown("### 📋 Tabla Completa de Valores SHAP")
                st.dataframe(shap_df, use_container_width=True, hide_index=True)
                    else:
                st.warning(explanation.get('message', 'SHAP no disponible para este tipo de modelo'))


# ==================== PÁGINA: ESTADÍSTICAS ====================
elif menu == "📈 Estadísticas":
    st.markdown('<div class="main-header">📈 Estadísticas de Uso</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="info-box">📊 Estadísticas de inferencias realizadas por el sistema.</div>', unsafe_allow_html=True)
    
    with st.spinner("Cargando estadísticas..."):
        stats = get_inference_stats()
    
    if not stats or "error" in stats:
        st.warning("⚠️ No hay estadísticas disponibles aún o hubo un error al cargarlas.")
        st.stop()
    
    # Métricas principales
    col1, col2, col3 = st.columns(3)
    col1.metric("🎯 Total de Inferencias", stats.get('total_inferences', 0))
    col2.metric("🕐 Últimas 24 horas", stats.get('recent_24h', 0))
    col3.metric("🤖 Modelos Únicos", len(stats.get('by_model_version', [])))
    
    st.markdown("---")
    
    # Inferencias por modelo
    if stats.get('by_model_version'):
        st.markdown('<div class="sub-header">📊 Inferencias por Versión de Modelo</div>', unsafe_allow_html=True)
        
        model_stats_df = pd.DataFrame(stats['by_model_version'])
        model_stats_df.columns = ['Versión del Modelo', 'Total Inferencias']
        
        fig = px.pie(
            model_stats_df,
            values='Total Inferencias',
            names='Versión del Modelo',
            title='Distribución de Inferencias por Modelo',
            hole=0.4
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(model_stats_df, use_container_width=True, hide_index=True)
    
    # Estado del sistema
    st.markdown("---")
    st.markdown('<div class="sub-header">🔧 Estado del Sistema</div>', unsafe_allow_html=True)
    
    if health:
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.markdown("**🔌 Conexión API**")
            st.success("Conectado" if health.get('status') == 'healthy' else "Degradado")
        
        with col_b:
            st.markdown("**🤖 Modelo Cargado**")
            st.success("Sí" if health.get('model_loaded') else "No")
        
        with col_c:
            st.markdown("**📡 MLflow URI**")
            st.info(health.get('mlflow_uri', 'N/A'))
    
    # Botón para recargar modelo
    st.markdown("---")
    if st.button("🔄 Recargar Modelo desde MLflow"):
        try:
            response = requests.post(f"{API_URL}/reload-model", timeout=10)
            if response.status_code == 200:
                st.success("✅ Modelo recargado exitosamente!")
                st.rerun()
            else:
                st.error("❌ Error al recargar el modelo")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
