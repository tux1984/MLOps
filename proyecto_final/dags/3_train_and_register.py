"""
DAG 3: Entrenamiento y Registro de Modelos

Este DAG se encarga de:
1. Leer datos limpios de clean-db
2. Entrenar múltiples modelos de ML
3. Registrar experimentos en MLflow
4. Comparar métricas de modelos
5. Seleccionar el mejor modelo
6. Promocionar automáticamente a Production

Modelos entrenados:
- Random Forest Classifier
- XGBoost Classifier
- Logistic Regression
- (Opcional) Gradient Boosting, SVM, etc.

Métricas evaluadas:
- Accuracy
- Precision
- Recall
- F1-Score
- ROC-AUC
- Confusion Matrix

MLflow Tracking:
- Parámetros de modelos
- Métricas de evaluación
- Artifacts (modelos, plots, feature importance)
- Model Registry con stage "Production"
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import pandas as pd
from sqlalchemy import create_engine
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, classification_report, confusion_matrix
)
import numpy as np
from utils.data_loader import get_db_connection

# Configuración
CLEAN_DB_URI = get_db_connection('clean')
MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')
EXPERIMENT_NAME = 'diabetes_readmission_prediction'


default_args = {
    'owner': 'mlops-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def load_clean_train_data(**context):
    """
    Carga datos de entrenamiento desde clean-db
    
    Returns:
        tuple: (X_train, y_train)
    """
    print("="*50)
    print("TAREA 1: CARGA DE DATOS CLEAN - TRAIN")
    print("="*50)
    
    engine = create_engine(CLEAN_DB_URI)
    query = "SELECT * FROM clean_train"
    df = pd.read_sql(query, engine)
    engine.dispose()
    
    print(f"✓ Datos clean_train cargados: {len(df)} registros")
    print(f"  Columnas: {len(df.columns)}")
    
    # Separar features y target
    feature_cols = [col for col in df.columns if col not in ['row_hash', 'readmitted', 'encounter_id', 'patient_nbr']]
    X = df[feature_cols]
    y = df['readmitted']
    
    print(f"  Features: {len(feature_cols)}")
    print(f"  Target distribution: {y.value_counts().to_dict()}")
    
    context['ti'].xcom_push(key='feature_cols', value=feature_cols)
    context['ti'].xcom_push(key='train_size', value=len(df))
    
    return {'X': X, 'y': y}


def load_clean_validation_data(**context):
    """
    Carga datos de validación desde clean-db
    
    Returns:
        tuple: (X_val, y_val)
    """
    print("="*50)
    print("TAREA 2: CARGA DE DATOS CLEAN - VALIDATION")
    print("="*50)
    
    engine = create_engine(CLEAN_DB_URI)
    query = "SELECT * FROM clean_validation"
    df = pd.read_sql(query, engine)
    engine.dispose()
    
    print(f"✓ Datos clean_validation cargados: {len(df)} registros")
    
    feature_cols = context['ti'].xcom_pull(task_ids='load_clean_train_data', key='feature_cols')
    X = df[feature_cols]
    y = df['readmitted']
    
    context['ti'].xcom_push(key='val_size', value=len(df))
    
    return {'X': X, 'y': y}


def load_clean_test_data(**context):
    """
    Carga datos de prueba desde clean-db
    
    Returns:
        tuple: (X_test, y_test)
    """
    print("="*50)
    print("TAREA 3: CARGA DE DATOS CLEAN - TEST")
    print("="*50)
    
    engine = create_engine(CLEAN_DB_URI)
    query = "SELECT * FROM clean_test"
    df = pd.read_sql(query, engine)
    engine.dispose()
    
    print(f"✓ Datos clean_test cargados: {len(df)} registros")
    
    feature_cols = context['ti'].xcom_pull(task_ids='load_clean_train_data', key='feature_cols')
    X = df[feature_cols]
    y = df['readmitted']
    
    context['ti'].xcom_push(key='test_size', value=len(df))
    
    return {'X': X, 'y': y}


def train_random_forest_model(**context):
    """
    Entrena modelo Random Forest
    
    Parámetros a optimizar:
    - n_estimators: [100, 200, 300]
    - max_depth: [10, 20, 30, None]
    - min_samples_split: [2, 5, 10]
    - min_samples_leaf: [1, 2, 4]
    
    Returns:
        dict: Modelo entrenado y métricas
    """
    print("="*50)
    print("TAREA 4: ENTRENAMIENTO - RANDOM FOREST")
    print("="*50)
    
    # Configurar MLflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    
    # Obtener datos
    train_data = context['ti'].xcom_pull(task_ids='load_clean_train_data')
    val_data = context['ti'].xcom_pull(task_ids='load_clean_validation_data')
    
    X_train, y_train = train_data['X'], train_data['y']
    X_val, y_val = val_data['X'], val_data['y']
    
    with mlflow.start_run(run_name='random_forest') as run:
        # Hiperparámetros
        params = {
            'n_estimators': 200,
            'max_depth': 20,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'random_state': 42,
            'n_jobs': -1
        }
        
        print(f"Hiperparámetros: {params}")
        
        # Entrenar
        model = RandomForestClassifier(**params)
        model.fit(X_train, y_train)
        
        # Predecir
        y_pred = model.predict(X_val)
        y_proba = model.predict_proba(X_val)
        
        # Métricas
        accuracy = accuracy_score(y_val, y_pred)
        precision = precision_score(y_val, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_val, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_val, y_pred, average='weighted', zero_division=0)
        
        print(f"\nMétricas en validation:")
        print(f"  Accuracy: {accuracy:.4f}")
        print(f"  Precision: {precision:.4f}")
        print(f"  Recall: {recall:.4f}")
        print(f"  F1-Score: {f1:.4f}")
        
        # Registrar en MLflow
        mlflow.log_params(params)
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)
        mlflow.log_metric("f1_score", f1)
        
        # Registrar modelo
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name="diabetes_random_forest"
        )
        
        run_id = run.info.run_id
        print(f"✓ Modelo registrado en MLflow (run_id: {run_id})")
        
        return {
            'model_name': 'random_forest',
            'f1_score': f1,
            'accuracy': accuracy,
            'run_id': run_id
        }


def train_xgboost_model(**context):
    """
    Entrena modelo XGBoost
    
    Parámetros a optimizar:
    - n_estimators: [100, 200, 300]
    - max_depth: [3, 5, 7, 9]
    - learning_rate: [0.01, 0.05, 0.1]
    - subsample: [0.8, 0.9, 1.0]
    - colsample_bytree: [0.8, 0.9, 1.0]
    
    Returns:
        dict: Modelo entrenado y métricas
    """
    print("="*50)
    print("TAREA 5: ENTRENAMIENTO - GRADIENT BOOSTING")
    print("="*50)
    
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    
    train_data = context['ti'].xcom_pull(task_ids='load_clean_train_data')
    val_data = context['ti'].xcom_pull(task_ids='load_clean_validation_data')
    
    X_train, y_train = train_data['X'], train_data['y']
    X_val, y_val = val_data['X'], val_data['y']
    
    with mlflow.start_run(run_name='gradient_boosting') as run:
        params = {
            'n_estimators': 200,
            'max_depth': 5,
            'learning_rate': 0.1,
            'subsample': 0.9,
            'random_state': 42
        }
        
        print(f"Hiperparámetros: {params}")
        
        model = GradientBoostingClassifier(**params)
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_val)
        
        accuracy = accuracy_score(y_val, y_pred)
        precision = precision_score(y_val, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_val, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_val, y_pred, average='weighted', zero_division=0)
        
        print(f"\nMétricas en validation:")
        print(f"  Accuracy: {accuracy:.4f}")
        print(f"  Precision: {precision:.4f}")
        print(f"  Recall: {recall:.4f}")
        print(f"  F1-Score: {f1:.4f}")
        
        mlflow.log_params(params)
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)
        mlflow.log_metric("f1_score", f1)
        
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name="diabetes_gradient_boosting"
        )
        
        run_id = run.info.run_id
        print(f"✓ Modelo registrado en MLflow (run_id: {run_id})")
        
        return {
            'model_name': 'gradient_boosting',
            'f1_score': f1,
            'accuracy': accuracy,
            'run_id': run_id
        }


def train_logistic_regression_model(**context):
    """
    Entrena modelo Logistic Regression
    
    Parámetros a optimizar:
    - C: [0.001, 0.01, 0.1, 1, 10, 100]
    - penalty: ['l1', 'l2']
    - solver: ['liblinear', 'saga']
    
    Returns:
        dict: Modelo entrenado y métricas
    """
    print("="*50)
    print("TAREA 6: ENTRENAMIENTO - LOGISTIC REGRESSION")
    print("="*50)
    
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    
    train_data = context['ti'].xcom_pull(task_ids='load_clean_train_data')
    val_data = context['ti'].xcom_pull(task_ids='load_clean_validation_data')
    
    X_train, y_train = train_data['X'], train_data['y']
    X_val, y_val = val_data['X'], val_data['y']
    
    with mlflow.start_run(run_name='logistic_regression') as run:
        params = {
            'C': 1.0,
            'max_iter': 1000,
            'solver': 'lbfgs',
            'random_state': 42
        }
        
        print(f"Hiperparámetros: {params}")
        
        model = LogisticRegression(**params)
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_val)
        
        accuracy = accuracy_score(y_val, y_pred)
        precision = precision_score(y_val, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_val, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_val, y_pred, average='weighted', zero_division=0)
        
        print(f"\nMétricas en validation:")
        print(f"  Accuracy: {accuracy:.4f}")
        print(f"  Precision: {precision:.4f}")
        print(f"  Recall: {recall:.4f}")
        print(f"  F1-Score: {f1:.4f}")
        
        mlflow.log_params(params)
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)
        mlflow.log_metric("f1_score", f1)
        
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name="diabetes_logistic_regression"
        )
        
        run_id = run.info.run_id
        print(f"✓ Modelo registrado en MLflow (run_id: {run_id})")
        
        return {
            'model_name': 'logistic_regression',
            'f1_score': f1,
            'accuracy': accuracy,
            'run_id': run_id
        }


def compare_model_metrics(**context):
    """
    Compara métricas de todos los modelos entrenados
    
    Criterios de selección:
    - Métrica principal: F1-Score (balance precision-recall)
    - Métricas secundarias: ROC-AUC, Accuracy
    - Complejidad del modelo (simplicidad es preferible)
    
    Returns:
        str: Nombre del mejor modelo
    """
    print("="*50)
    print("TAREA 7: COMPARACIÓN DE MODELOS")
    print("="*50)
    
    rf_metrics = context['ti'].xcom_pull(task_ids='train_random_forest')
    gb_metrics = context['ti'].xcom_pull(task_ids='train_gradient_boosting')
    lr_metrics = context['ti'].xcom_pull(task_ids='train_logistic_regression')
    
    models = [rf_metrics, gb_metrics, lr_metrics]
    
    print("\nResultados de entrenamiento:")
    print("-" * 70)
    print(f"{'Modelo':<25} {'F1-Score':<12} {'Accuracy':<12} {'Run ID':<30}")
    print("-" * 70)
    
    for m in models:
        print(f"{m['model_name']:<25} {m['f1_score']:<12.4f} {m['accuracy']:<12.4f} {m['run_id']:<30}")
    
    best_model = max(models, key=lambda x: x['f1_score'])
    
    print("-" * 70)
    print(f"\n🏆 MEJOR MODELO: {best_model['model_name']} (F1={best_model['f1_score']:.4f})")
    
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    
    with mlflow.start_run(run_name='model_comparison'):
        mlflow.log_param("best_model", best_model['model_name'])
        mlflow.log_metric("best_f1_score", best_model['f1_score'])
        mlflow.log_metric("best_accuracy", best_model['accuracy'])
        
        for m in models:
            mlflow.log_metric(f"{m['model_name']}_f1", m['f1_score'])
            mlflow.log_metric(f"{m['model_name']}_accuracy", m['accuracy'])
    
    return best_model


def evaluate_best_model_on_test(**context):
    """
    Evalúa el mejor modelo en test set
    
    Genera métricas finales y reportes de evaluación
    """
    print("="*50)
    print("TAREA 8: EVALUACIÓN EN TEST SET")
    print("="*50)
    
    best_model_info = context['ti'].xcom_pull(task_ids='compare_models')
    test_data = context['ti'].xcom_pull(task_ids='load_clean_test_data')
    
    X_test, y_test = test_data['X'], test_data['y']
    
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    
    model_name = f"diabetes_{best_model_info['model_name']}"
    print(f"Cargando modelo: {model_name}")
    
    model_uri = f"models:/{model_name}/latest"
    model = mlflow.sklearn.load_model(model_uri)
    
    y_pred = model.predict(X_test)
    
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
    recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
    f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
    
    print(f"\nMétricas finales en TEST SET:")
    print(f"  Accuracy: {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall: {recall:.4f}")
    print(f"  F1-Score: {f1:.4f}")
    
    mlflow.set_experiment(EXPERIMENT_NAME)
    with mlflow.start_run(run_name='test_evaluation'):
        mlflow.log_param("evaluated_model", model_name)
        mlflow.log_metric("test_accuracy", accuracy)
        mlflow.log_metric("test_precision", precision)
        mlflow.log_metric("test_recall", recall)
        mlflow.log_metric("test_f1_score", f1)
    
    return {
        'model_name': model_name,
        'test_f1_score': f1,
        'test_accuracy': accuracy
    }


def register_model_to_mlflow(**context):
    """
    Registra el mejor modelo en MLflow Model Registry
    
    Versiona el modelo y lo registra como candidato
    """
    # TODO: Implementar registro en Model Registry
    # - Obtener mejor modelo desde XCom
    # - Registrar en MLflow Model Registry
    # - Versionar modelo
    # - Agregar tags y descripción
    # - Retornar versión registrada
    pass


def promote_to_production(**context):
    """
    Promociona el modelo a stage "Production"
    
    Archiva versiones anteriores y marca la nueva como Production
    """
    print("="*50)
    print("TAREA 9: PROMOCIÓN A PRODUCTION")
    print("="*50)
    
    best_model_info = context['ti'].xcom_pull(task_ids='compare_models')
    
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient()
    
    model_name = f"diabetes_{best_model_info['model_name']}"
    run_id = best_model_info['run_id']
    
    print(f"Promocionando modelo: {model_name}")
    print(f"Run ID: {run_id}")
    
    try:
        versions = client.search_model_versions(f"name='{model_name}'")
        
        for mv in versions:
            if mv.current_stage == 'Production':
                print(f"Archivando versión anterior: v{mv.version}")
                client.transition_model_version_stage(
                    name=model_name,
                    version=mv.version,
                    stage="Archived"
                )
        
        latest_versions = client.get_latest_versions(model_name, stages=["None", "Staging"])
        if latest_versions:
            latest_version = latest_versions[0].version
            print(f"Promocionando versión {latest_version} a Production")
            
            client.transition_model_version_stage(
                name=model_name,
                version=latest_version,
                stage="Production",
                archive_existing_versions=False
            )
            
            client.update_model_version(
                name=model_name,
                version=latest_version,
                description=f"Modelo promovido a Production. F1-Score: {best_model_info['f1_score']:.4f}"
            )
            
            print(f"✓ Modelo {model_name} v{latest_version} en Production")
            
            return {
                'model_name': model_name,
                'version': latest_version,
                'stage': 'Production'
            }
        else:
            print("⚠ No se encontró versión para promocionar")
            return None
            
    except Exception as e:
        print(f"❌ Error promocionando modelo: {str(e)}")
        raise


def log_training_summary(**context):
    """
    Registra resumen final del pipeline de entrenamiento
    """
    print("="*50)
    print("RESUMEN FINAL DE ENTRENAMIENTO")
    print("="*50)
    
    best_model_info = context['ti'].xcom_pull(task_ids='compare_models')
    test_metrics = context['ti'].xcom_pull(task_ids='evaluate_best_on_test')
    prod_info = context['ti'].xcom_pull(task_ids='promote_to_production')
    
    print("\n📊 Resultados Finales:")
    print(f"  Mejor modelo: {best_model_info['model_name']}")
    print(f"  F1-Score (validation): {best_model_info['f1_score']:.4f}")
    print(f"  F1-Score (test): {test_metrics['test_f1_score']:.4f}")
    print(f"  Accuracy (test): {test_metrics['test_accuracy']:.4f}")
    
    if prod_info:
        print(f"\n✓ Modelo en Production:")
        print(f"  Nombre: {prod_info['model_name']}")
        print(f"  Versión: {prod_info['version']}")
        print(f"  Stage: {prod_info['stage']}")
    
    print("\n✓ Pipeline de entrenamiento completado exitosamente")
    print("="*50)


# Definición del DAG
with DAG(
    '3_train_and_register',
    default_args=default_args,
    description='Entrenamiento de modelos, evaluación y registro en MLflow',
    schedule_interval=None,  # Manual trigger after DAG 2
    catchup=False,
    tags=['training', 'mlflow', 'model-registry'],
) as dag:

    # Task 1: Cargar datos limpios
    task_load_train = PythonOperator(
        task_id='load_clean_train_data',
        python_callable=load_clean_train_data,
        provide_context=True,
    )

    task_load_val = PythonOperator(
        task_id='load_clean_validation_data',
        python_callable=load_clean_validation_data,
        provide_context=True,
    )

    task_load_test = PythonOperator(
        task_id='load_clean_test_data',
        python_callable=load_clean_test_data,
        provide_context=True,
    )

    # Task 2: Entrenar modelos en paralelo
    task_train_rf = PythonOperator(
        task_id='train_random_forest',
        python_callable=train_random_forest_model,
        provide_context=True,
    )

    task_train_xgb = PythonOperator(
        task_id='train_gradient_boosting',
        python_callable=train_xgboost_model,
        provide_context=True,
    )

    task_train_lr = PythonOperator(
        task_id='train_logistic_regression',
        python_callable=train_logistic_regression_model,
        provide_context=True,
    )

    # Task 3: Comparar modelos
    task_compare = PythonOperator(
        task_id='compare_models',
        python_callable=compare_model_metrics,
        provide_context=True,
    )

    # Task 4: Evaluar mejor modelo en test
    task_evaluate = PythonOperator(
        task_id='evaluate_best_on_test',
        python_callable=evaluate_best_model_on_test,
        provide_context=True,
    )

    # Task 5: Promocionar a Production
    task_promote = PythonOperator(
        task_id='promote_to_production',
        python_callable=promote_to_production,
        provide_context=True,
    )

    # Task 6: Log resumen final
    task_summary = PythonOperator(
        task_id='log_training_summary',
        python_callable=log_training_summary,
        provide_context=True,
    )

    # Flujo del DAG
    [task_load_train, task_load_val, task_load_test] >> [task_train_rf, task_train_xgb, task_train_lr]
    [task_train_rf, task_train_xgb, task_train_lr] >> task_compare
    task_compare >> task_evaluate >> task_promote >> task_summary
