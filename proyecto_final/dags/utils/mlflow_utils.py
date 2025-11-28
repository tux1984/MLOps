"""
Módulo de utilidades para MLflow

Funciones para:
- Logging de experimentos
- Registro de modelos
- Promoción de modelos a Production
- Comparación de modelos
- Obtención de mejor modelo
"""

from typing import Dict, List, Any, Optional, Tuple
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
import pandas as pd
from datetime import datetime


def setup_mlflow(tracking_uri: str, experiment_name: str) -> str:
    """
    Configura MLflow tracking
    
    Args:
        tracking_uri: URI del servidor de tracking
        experiment_name: Nombre del experimento
    
    Returns:
        str: ID del experimento
    """
    # TODO: Implementar
    # - Set tracking URI
    # - Create o get experiment
    # - Retornar experiment_id
    pass


def log_model_training(
    run_name: str,
    model,
    model_name: str,
    params: Dict,
    metrics: Dict,
    artifacts: Optional[Dict] = None,
    tags: Optional[Dict] = None
) -> str:
    """
    Registra un experimento de entrenamiento en MLflow
    
    Args:
        run_name: Nombre del run
        model: Modelo entrenado
        model_name: Nombre del modelo
        params: Hiperparámetros del modelo
        metrics: Métricas de evaluación
        artifacts: Artifacts adicionales (plots, etc)
        tags: Tags para el run
    
    Returns:
        str: Run ID
    """
    # TODO: Implementar
    # - Iniciar run con mlflow.start_run()
    # - Log params con mlflow.log_params()
    # - Log metrics con mlflow.log_metrics()
    # - Log model con mlflow.sklearn.log_model()
    # - Log artifacts si existen
    # - Set tags si existen
    # - Retornar run_id
    pass


def register_model(
    run_id: str,
    model_name: str,
    description: Optional[str] = None
) -> str:
    """
    Registra un modelo en MLflow Model Registry
    
    Args:
        run_id: ID del run con el modelo
        model_name: Nombre para el modelo registrado
        description: Descripción del modelo
    
    Returns:
        str: Versión del modelo registrado
    """
    # TODO: Implementar
    # - Get model URI from run
    # - Register model con mlflow.register_model()
    # - Agregar descripción si existe
    # - Retornar versión
    pass


def promote_model_to_production(
    model_name: str,
    version: Optional[str] = None
) -> Dict:
    """
    Promociona un modelo a stage Production
    
    Args:
        model_name: Nombre del modelo
        version: Versión específica (None = última versión)
    
    Returns:
        dict: Información de la promoción
    """
    # TODO: Implementar
    # - Get MLflow client
    # - Si version es None, obtener última versión
    # - Archivar versiones anteriores en Production
    # - Transicionar nueva versión a Production
    # - Retornar información de promoción
    pass


def compare_models(
    run_ids: List[str],
    metric: str = 'f1_score'
) -> pd.DataFrame:
    """
    Compara métricas de múltiples modelos
    
    Args:
        run_ids: Lista de run IDs a comparar
        metric: Métrica principal de comparación
    
    Returns:
        pd.DataFrame: Tabla comparativa de modelos
    """
    # TODO: Implementar
    # - Get MLflow client
    # - Para cada run_id:
    #   - Obtener run info
    #   - Extraer métricas
    #   - Agregar a lista
    # - Crear DataFrame con comparación
    # - Ordenar por métrica principal
    # - Retornar DataFrame
    pass


def get_best_model(
    experiment_name: str,
    metric: str = 'f1_score',
    minimize: bool = False
) -> Tuple[str, Dict]:
    """
    Obtiene el mejor modelo de un experimento
    
    Args:
        experiment_name: Nombre del experimento
        metric: Métrica para determinar mejor modelo
        minimize: Si True, menor es mejor. Si False, mayor es mejor
    
    Returns:
        tuple: (run_id, metrics_dict)
    """
    # TODO: Implementar
    # - Buscar experimento
    # - Obtener todos los runs del experimento
    # - Ordenar por métrica
    # - Retornar mejor run_id y métricas
    pass


def load_production_model(model_name: str):
    """
    Carga el modelo en stage Production
    
    Args:
        model_name: Nombre del modelo registrado
    
    Returns:
        Model: Modelo cargado
    """
    # TODO: Implementar
    # - Get MLflow client
    # - Buscar versión en Production
    # - Cargar modelo con mlflow.pyfunc.load_model()
    # - Retornar modelo
    pass


def get_model_metadata(
    model_name: str,
    stage: str = "Production"
) -> Dict:
    """
    Obtiene metadata de un modelo registrado
    
    Args:
        model_name: Nombre del modelo
        stage: Stage del modelo
    
    Returns:
        dict: Metadata del modelo
    """
    # TODO: Implementar
    # - Get MLflow client
    # - Obtener versión en stage especificado
    # - Obtener run asociado
    # - Extraer metadata (params, metrics, tags, etc)
    # - Retornar diccionario con metadata
    pass


def log_feature_importance(
    feature_names: List[str],
    importances: List[float],
    plot_path: Optional[str] = None
) -> None:
    """
    Registra feature importance en MLflow
    
    Args:
        feature_names: Nombres de features
        importances: Importancia de cada feature
        plot_path: Path del plot de importancia (opcional)
    """
    # TODO: Implementar
    # - Crear DataFrame con features e importances
    # - Log como artifact
    # - Si plot_path existe, loggearlo también
    pass


def log_confusion_matrix(
    y_true: List,
    y_pred: List,
    labels: Optional[List] = None
) -> None:
    """
    Calcula y registra confusion matrix en MLflow
    
    Args:
        y_true: Labels verdaderos
        y_pred: Labels predichos
        labels: Nombres de las clases
    """
    # TODO: Implementar
    # - Calcular confusion matrix con sklearn
    # - Crear visualización con matplotlib/seaborn
    # - Guardar plot
    # - Log como artifact en MLflow
    pass


def log_roc_curve(
    y_true: List,
    y_proba: List,
    model_name: str
) -> None:
    """
    Calcula y registra ROC curve en MLflow
    
    Args:
        y_true: Labels verdaderos
        y_proba: Probabilidades predichas
        model_name: Nombre del modelo para el título
    """
    # TODO: Implementar
    # - Calcular ROC curve con sklearn
    # - Crear plot con matplotlib
    # - Guardar plot
    # - Log como artifact en MLflow
    pass


def search_runs_by_metric(
    experiment_name: str,
    metric: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> pd.DataFrame:
    """
    Busca runs por valor de métrica
    
    Args:
        experiment_name: Nombre del experimento
        metric: Nombre de la métrica
        min_value: Valor mínimo de la métrica
        max_value: Valor máximo de la métrica
    
    Returns:
        pd.DataFrame: Runs que cumplen el criterio
    """
    # TODO: Implementar
    # - Construir filter string para mlflow.search_runs()
    # - Buscar runs
    # - Retornar DataFrame con resultados
    pass
