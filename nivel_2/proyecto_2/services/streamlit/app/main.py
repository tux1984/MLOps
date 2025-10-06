"""
Forest Cover Classification - Streamlit Web Application

This application provides an interactive interface for the Forest Cover Classification ML pipeline.
It allows users to make predictions, visualize data, and monitor model performance.
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime
from typing import Dict, List, Any
import os

# Configure Streamlit page
st.set_page_config(
    page_title="Forest Cover Classification",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2E8B57;
    }
    .prediction-result {
        background-color: #e8f5e8;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 2px solid #2E8B57;
        text-align: center;
    }
    .error-message {
        background-color: #ffe6e6;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 2px solid #ff4444;
        color: #cc0000;
    }
    .info-box {
        background-color: #e6f3ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #0066cc;
    }
</style>
""", unsafe_allow_html=True)

# Configuration
API_BASE_URL = os.getenv("INFERENCE_API_URL", "http://inference:8000")
MLFLOW_URL = os.getenv("MLFLOW_URL", "http://mlflow:5000")

class ForestCoverApp:
    """Main application class for Forest Cover Classification"""
    
    def __init__(self):
        self.api_url = API_BASE_URL
        self.mlflow_url = MLFLOW_URL
        
    def check_api_health(self) -> bool:
        """Check if the inference API is healthy"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def get_model_metadata(self) -> Dict[str, Any]:
        """Get model metadata from the API"""
        try:
            response = requests.get(f"{self.api_url}/metadata", timeout=5)
            if response.status_code == 200:
                return response.json()
            return {}
        except requests.exceptions.RequestException:
            return {}
    
    def make_prediction(self, sample_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Make prediction using the API"""
        try:
            payload = {"samples": sample_data}
            response = requests.post(
                f"{self.api_url}/predict", 
                json=payload, 
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API Error: {response.status_code} - {response.text}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Connection Error: {str(e)}"}

def render_header():
    """Render the application header"""
    st.markdown('<h1 class="main-header">🌲 Forest Cover Classification</h1>', unsafe_allow_html=True)
    st.markdown("---")

def render_sidebar():
    """Render the sidebar with navigation and model info"""
    st.sidebar.title("🧭 Navegación")
    
    # Model status
    app = ForestCoverApp()
    is_healthy = app.check_api_health()
    
    if is_healthy:
        st.sidebar.success("✅ API Conectada")
        metadata = app.get_model_metadata()
        if metadata:
            st.sidebar.markdown("### 📊 Información del Modelo")
            st.sidebar.write(f"**Nombre del Modelo:** {metadata.get('model_name', 'N/A')}")
            st.sidebar.write(f"**Versión:** {metadata.get('version', 'N/A')[:8]}...")
            st.sidebar.write(f"**Entrenado en:** {metadata.get('trained_at', 'N/A')}")
            st.sidebar.write(f"**Características:** {len(metadata.get('feature_names', []))}")
    else:
        st.sidebar.error("❌ API Desconectada")
        st.sidebar.info("Por favor, asegúrate de que el servicio de inferencia esté ejecutándose.")
    
    st.sidebar.markdown("---")
    
    # Navigation
    st.sidebar.markdown("### 📋 Páginas")
    return st.sidebar.radio(
        "Seleccionar una página:",
        ["🏠 Inicio", "🔮 Predicciones", "📈 Analíticas", "📊 Info del Modelo", "🔧 Configuración"]
    )

def render_home_page():
    """Render the home page with overview"""
    st.markdown("## 🏠 Bienvenido a la Clasificación de Cobertura Forestal")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Acerca de Esta Aplicación
        
        Esta aplicación proporciona una interfaz interactiva para predecir tipos de cobertura forestal
        basándose en variables cartográficas. El modelo utiliza aprendizaje automático para clasificar
        áreas forestales en diferentes tipos de cobertura.
        
        **Características Principales:**
        - 🌲 **Predicciones en Tiempo Real**: Realiza predicciones con datos de entrada personalizados
        - 📊 **Visualización de Datos**: Explora patrones en los datos de cobertura forestal
        - 📈 **Analíticas del Modelo**: Monitorea el rendimiento y métricas del modelo
        - 🔧 **Configuración Fácil**: Interfaz simple para todos los niveles de habilidad
        """)
        
        st.markdown("### 🎯 Tipos de Cobertura Forestal")
        cover_types = {
            0: "Spruce/Fir",
            1: "Lodgepole Pine", 
            2: "Ponderosa Pine",
            3: "Cottonwood/Willow",
            4: "Aspen",
            5: "Douglas-fir",
            6: "Krummholz"
        }
        
        for cover_type, description in cover_types.items():
            st.write(f"**{cover_type}:** {description}")
    
    with col2:
        # Quick stats
        app = ForestCoverApp()
        metadata = app.get_model_metadata()
        
        st.markdown("### 📊 Estadísticas Rápidas")
        
        if metadata:
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Versión del Modelo", metadata.get('version', 'N/A')[:8] + "...")
            with col_b:
                st.metric("Características", len(metadata.get('feature_names', [])))
            
            st.markdown("### 🎯 ¿Listo para Predecir?")
            if st.button("🚀 Ir a Predicciones", type="primary"):
                st.session_state.page = "🔮 Predict"
                st.rerun()

def render_prediction_page():
    """Render the prediction page"""
    st.markdown("## 🔮 Realizar Predicciones")
    
    # Create tabs for different input methods
    tab1, tab2, tab3 = st.tabs(["📝 Predicción Individual", "📊 Predicción por Lotes", "📁 Subir CSV"])
    
    with tab1:
        render_single_prediction()
    
    with tab2:
        render_batch_prediction()
    
    with tab3:
        render_csv_upload()

def render_single_prediction():
    """Render single prediction form"""
    st.markdown("### 📝 Predicción de Muestra Individual")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🌍 Características Geográficas")
        elevation = st.number_input("Elevación (metros)", min_value=0, max_value=5000, value=2596)
        aspect = st.number_input("Aspecto (grados)", min_value=0, max_value=360, value=51)
        slope = st.number_input("Pendiente (grados)", min_value=0, max_value=90, value=3)
        
        st.markdown("#### 💧 Características de Hidrología")
        h_dist_hydrology = st.number_input("Distancia Horizontal a Hidrología", min_value=0, max_value=2000, value=258)
        v_dist_hydrology = st.number_input("Distancia Vertical a Hidrología", min_value=-1000, max_value=1000, value=0)
        
        st.markdown("#### 🛣️ Características de Infraestructura")
        h_dist_roadways = st.number_input("Distancia Horizontal a Carreteras", min_value=0, max_value=7000, value=510)
        h_dist_fire = st.number_input("Distancia Horizontal a Puntos de Fuego", min_value=0, max_value=10000, value=6279)
    
    with col2:
        st.markdown("#### ☀️ Características de Sombra")
        hillshade_9am = st.number_input("Sombra a las 9am", min_value=0, max_value=255, value=211)
        hillshade_noon = st.number_input("Sombra al Mediodía", min_value=0, max_value=255, value=232)
        hillshade_3pm = st.number_input("Sombra a las 3pm", min_value=0, max_value=255, value=148)
        
        st.markdown("#### 🌿 Características Ambientales")
        wilderness_area = st.selectbox(
            "Área Silvestre",
            ["Rawah", "Neota", "Comanche Peak", "Cache la Poudre"],
            index=0
        )
        
        soil_type = st.selectbox(
            "Tipo de Suelo",
            ["C7745", "C7756", "C7711", "C7201", "C7702", "C7709", "C7717", "C7700", 
             "C7746", "C7715", "C7710", "C7701", "C7704", "C7744", "C7703", "C7705",
             "C7713", "C7718", "C7712", "C7706", "C7707", "C7708", "C7714", "C7716",
             "C7719", "C7720", "C7721", "C7722", "C7723", "C7724", "C7725", "C7726",
             "C7727", "C7728", "C7729", "C7730", "C7731", "C7732", "C7733", "C7734"],
            index=0
        )
    
    # Prediction button
    if st.button("🔮 Predecir Tipo de Cobertura Forestal", type="primary", use_container_width=True):
        sample_data = {
            "elevation": int(elevation),
            "aspect": int(aspect),
            "slope": int(slope),
            "horizontal_distance_to_hydrology": int(h_dist_hydrology),
            "vertical_distance_to_hydrology": int(v_dist_hydrology),
            "horizontal_distance_to_roadways": int(h_dist_roadways),
            "hillshade_9am": int(hillshade_9am),
            "hillshade_noon": int(hillshade_noon),
            "hillshade_3pm": int(hillshade_3pm),
            "horizontal_distance_to_fire_points": int(h_dist_fire),
            "wilderness_area": wilderness_area,
            "soil_type": soil_type
        }
        
        app = ForestCoverApp()
        result = app.make_prediction([sample_data])
        
        if "error" in result:
            st.markdown(f'<div class="error-message">❌ {result["error"]}</div>', unsafe_allow_html=True)
        else:
            prediction = result["predictions"][0]
            cover_types = {
                0: "Spruce/Fir",
                1: "Lodgepole Pine", 
                2: "Ponderosa Pine",
                3: "Cottonwood/Willow",
                4: "Aspen",
                5: "Douglas-fir",
                6: "Krummholz"
            }
            
            cover_type = cover_types.get(prediction, f"Unknown Type {prediction}")
            
            st.markdown(f'''
            <div class="prediction-result">
                <h3>🎯 Resultado de la Predicción</h3>
                <h2>Tipo de Cobertura Forestal: {prediction}</h2>
                <h3>{cover_type}</h3>
                <p><strong>Versión del Modelo:</strong> {result["model_version"][:8]}...</p>
            </div>
            ''', unsafe_allow_html=True)

def render_batch_prediction():
    """Render batch prediction interface"""
    st.markdown("### 📊 Predicción por Lotes")
    st.info("Ingresa múltiples muestras a continuación. Cada fila representa una muestra.")
    
    # Create editable dataframe
    sample_data = pd.DataFrame({
        'elevation': [2596, 3052],
        'aspect': [51, 80],
        'slope': [3, 4],
        'horizontal_distance_to_hydrology': [258, 170],
        'vertical_distance_to_hydrology': [0, 38],
        'horizontal_distance_to_roadways': [510, 85],
        'hillshade_9am': [211, 225],
        'hillshade_noon': [232, 232],
        'hillshade_3pm': [148, 142],
        'horizontal_distance_to_fire_points': [6279, 716],
        'wilderness_area': ['Rawah', 'Rawah'],
        'soil_type': ['C7745', 'C7201']
    })
    
    edited_df = st.data_editor(
        sample_data,
        num_rows="dynamic",
        use_container_width=True,
        key="batch_editor"
    )
    
    if st.button("🔮 Predecir Todas las Muestras", type="primary"):
        # Convert dataframe to list of dicts
        samples = edited_df.to_dict('records')
        
        app = ForestCoverApp()
        result = app.make_prediction(samples)
        
        if "error" in result:
            st.markdown(f'<div class="error-message">❌ {result["error"]}</div>', unsafe_allow_html=True)
        else:
            # Add predictions to dataframe
            edited_df['prediction'] = result['predictions']
            edited_df['cover_type'] = edited_df['prediction'].map({
                0: "Spruce/Fir", 1: "Lodgepole Pine", 2: "Ponderosa Pine",
                3: "Cottonwood/Willow", 4: "Aspen", 5: "Douglas-fir", 6: "Krummholz"
            })
            
            st.success(f"✅ ¡Se predijeron exitosamente {len(result['predictions'])} muestras!")
            st.dataframe(edited_df[['elevation', 'aspect', 'slope', 'prediction', 'cover_type']], use_container_width=True)
            
            # Show prediction distribution
            fig = px.pie(
                values=edited_df['cover_type'].value_counts().values,
                names=edited_df['cover_type'].value_counts().index,
                title="Distribución de Predicciones"
            )
            st.plotly_chart(fig, use_container_width=True)

def render_csv_upload():
    """Render CSV upload interface"""
    st.markdown("### 📁 Subir Archivo CSV")
    st.info("Sube un archivo CSV con las columnas requeridas. Ve el formato de muestra a continuación.")
    
    # Show sample format
    sample_data = pd.DataFrame({
        'elevation': [2596, 3052],
        'aspect': [51, 80],
        'slope': [3, 4],
        'horizontal_distance_to_hydrology': [258, 170],
        'vertical_distance_to_hydrology': [0, 38],
        'horizontal_distance_to_roadways': [510, 85],
        'hillshade_9am': [211, 225],
        'hillshade_noon': [232, 232],
        'hillshade_3pm': [148, 142],
        'horizontal_distance_to_fire_points': [6279, 716],
        'wilderness_area': ['Rawah', 'Rawah'],
        'soil_type': ['C7745', 'C7201']
    })
    
    with st.expander("📋 Formato CSV Requerido"):
        st.dataframe(sample_data, use_container_width=True)
    
    uploaded_file = st.file_uploader("Elegir un archivo CSV", type="csv")
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.success(f"✅ Se cargaron exitosamente {len(df)} filas")
            st.dataframe(df.head(), use_container_width=True)
            
            if st.button("🔮 Predecir Todas las Filas", type="primary"):
                # Convert to required format
                samples = df.to_dict('records')
                
                app = ForestCoverApp()
                result = app.make_prediction(samples)
                
                if "error" in result:
                    st.markdown(f'<div class="error-message">❌ {result["error"]}</div>', unsafe_allow_html=True)
                else:
                    df['prediction'] = result['predictions']
                    df['cover_type'] = df['prediction'].map({
                        0: "Spruce/Fir", 1: "Lodgepole Pine", 2: "Ponderosa Pine",
                        3: "Cottonwood/Willow", 4: "Aspen", 5: "Douglas-fir", 6: "Krummholz"
                    })
                    
                    st.success(f"✅ ¡Se predijeron exitosamente {len(result['predictions'])} muestras!")
                    
                    # Download results
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Descargar Resultados",
                        data=csv,
                        file_name=f"forest_cover_predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    
                    st.dataframe(df, use_container_width=True)
                    
        except Exception as e:
            st.error(f"❌ Error al leer el archivo CSV: {str(e)}")

def render_analytics_page():
    """Render analytics and visualization page"""
    st.markdown("## 📈 Analíticas de Datos")
    
    # Sample data for demonstration
    sample_data = {
        'elevation': [2596, 3052, 2489, 2856, 3100],
        'aspect': [51, 80, 45, 120, 200],
        'slope': [3, 4, 2, 5, 8],
        'horizontal_distance_to_hydrology': [258, 170, 300, 150, 400],
        'vertical_distance_to_hydrology': [0, 38, -10, 25, 50],
        'horizontal_distance_to_roadways': [510, 85, 600, 200, 800],
        'hillshade_9am': [211, 225, 200, 230, 240],
        'hillshade_noon': [232, 232, 220, 240, 250],
        'hillshade_3pm': [148, 142, 150, 160, 170],
        'horizontal_distance_to_fire_points': [6279, 716, 5000, 1000, 8000],
        'wilderness_area': ['Rawah', 'Rawah', 'Neota', 'Comanche Peak', 'Cache la Poudre'],
        'soil_type': ['C7745', 'C7201', 'C7756', 'C7711', 'C7702'],
        'cover_type': [0, 1, 2, 0, 3]
    }
    
    df = pd.DataFrame(sample_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🌲 Distribución de Tipos de Cobertura")
        fig = px.pie(
            values=df['cover_type'].value_counts().values,
            names=df['cover_type'].value_counts().index,
            title="Distribución de Tipos de Cobertura Forestal"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 📊 Distancia a Carreteras vs Elevación")
        fig = px.scatter(
            df, x='horizontal_distance_to_roadways', y='elevation', 
            color='cover_type',
            title="Distancia Horizontal a Carreteras vs Elevación por Tipo de Cobertura",
            labels={'horizontal_distance_to_roadways': 'Distancia a Carreteras (m)', 
                   'elevation': 'Elevación (m)',
                   'cover_type': 'Tipo de Cobertura'}
        )
        fig.update_layout(
            xaxis_title="Distancia a Carreteras (metros)",
            yaxis_title="Elevación (metros)"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("### 📊 Correlaciones de Características")
    numeric_features = ['elevation', 'aspect', 'slope', 'horizontal_distance_to_hydrology', 
                       'vertical_distance_to_hydrology', 'horizontal_distance_to_roadways',
                       'hillshade_9am', 'hillshade_noon', 'hillshade_3pm', 
                       'horizontal_distance_to_fire_points']
    
    corr_matrix = df[numeric_features].corr()
    fig = px.imshow(corr_matrix, text_auto=True, aspect="auto", title="Matriz de Correlación de Características")
    st.plotly_chart(fig, use_container_width=True)

def render_model_info_page():
    """Render model information page"""
    st.markdown("## 📊 Información del Modelo")
    
    app = ForestCoverApp()
    metadata = app.get_model_metadata()
    
    if metadata:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🎯 Detalles del Modelo")
            st.info(f"""
            **Nombre del Modelo:** {metadata.get('model_name', 'N/A')}  
            **Versión:** {metadata.get('version', 'N/A')}  
            **Entrenado en:** {metadata.get('trained_at', 'N/A')}  
            **Número de Características:** {len(metadata.get('feature_names', []))}
            """)
            
            st.markdown("### 🔧 Características")
            feature_names = metadata.get('feature_names', [])
            if feature_names:
                feature_df = pd.DataFrame({'Feature': feature_names})
                st.dataframe(feature_df, use_container_width=True)
        
        with col2:
            st.markdown("### 🌲 Tipos de Cobertura Forestal")
            cover_types = {
                0: "Spruce/Fir",
                1: "Lodgepole Pine",
                2: "Ponderosa Pine", 
                3: "Cottonwood/Willow",
                4: "Aspen",
                5: "Douglas-fir",
                6: "Krummholz"
            }
            
            for cover_type, description in cover_types.items():
                st.write(f"**{cover_type}:** {description}")
            
            st.markdown("### 📈 Rendimiento del Modelo")
            st.info("Las métricas de rendimiento del modelo están disponibles en el seguimiento de MLflow.")
            
            if st.button("🔗 Abrir MLflow UI", type="secondary"):
                st.markdown(f"[Abrir MLflow UI](http://localhost:5000)")
            
            if st.button("🔗 Abrir API de Inferencia", type="secondary"):
                st.markdown(f"[Abrir API de Inferencia](http://localhost:8000)")
    else:
        st.error("❌ No se pudo recuperar la metadata del modelo. Por favor, verifica la conexión de la API.")

def render_settings_page():
    """Render settings page"""
    st.markdown("## 🔧 Configuración")
    
    st.markdown("### 🌐 Configuración de API")
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("URL de API de Inferencia", value="http://localhost:8000", disabled=True)
        st.text_input("URL de MLflow", value="http://localhost:5000", disabled=True)
    
    with col2:
        if st.button("🔄 Actualizar Conexión API"):
            st.rerun()
    
    st.markdown("### 📊 Configuración de Visualización")
    col1, col2 = st.columns(2)
    
    with col1:
        st.selectbox("Tema", ["Light", "Dark"], index=0)
        st.selectbox("Estilo de Gráficos", ["Plotly", "Matplotlib"], index=0)
    
    with col2:
        st.slider("Ancho de Gráficos", 50, 100, 100)
        st.checkbox("Mostrar Tablas de Datos", value=True)

def main():
    """Main application function"""
    render_header()
    
    # Navigation
    selected_page = render_sidebar()
    
    # Route to appropriate page
    if selected_page == "🏠 Inicio":
        render_home_page()
    elif selected_page == "🔮 Predicciones":
        render_prediction_page()
    elif selected_page == "📈 Analíticas":
        render_analytics_page()
    elif selected_page == "📊 Info del Modelo":
        render_model_info_page()
    elif selected_page == "🔧 Configuración":
        render_settings_page()

if __name__ == "__main__":
    main()
