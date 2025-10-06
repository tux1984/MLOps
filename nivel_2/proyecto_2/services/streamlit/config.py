"""
Configuration settings for the Streamlit application
"""

import os
from typing import Dict, Any

class Config:
    """Application configuration class"""
    
    # API Configuration
    INFERENCE_API_URL = os.getenv("INFERENCE_API_URL", "http://inference:8000")
    MLFLOW_URL = os.getenv("MLFLOW_URL", "http://mlflow:5000")
    
    # Streamlit Configuration
    APP_TITLE = os.getenv("APP_TITLE", "Forest Cover Classification")
    APP_ICON = os.getenv("APP_ICON", "🌲")
    PAGE_LAYOUT = os.getenv("PAGE_LAYOUT", "wide")
    
    # Feature Configuration
    NUMERIC_FEATURES = [
        "elevation",
        "aspect", 
        "slope",
        "horizontal_distance_to_hydrology",
        "vertical_distance_to_hydrology",
        "horizontal_distance_to_roadways",
        "hillshade_9am",
        "hillshade_noon", 
        "hillshade_3pm",
        "horizontal_distance_to_fire_points"
    ]
    
    CATEGORICAL_FEATURES = [
        "wilderness_area",
        "soil_type"
    ]
    
    # Forest Cover Types
    COVER_TYPES = {
        0: "Spruce/Fir",
        1: "Lodgepole Pine",
        2: "Ponderosa Pine", 
        3: "Cottonwood/Willow",
        4: "Aspen",
        5: "Douglas-fir",
        6: "Krummholz"
    }
    
    # Wilderness Areas
    WILDERNESS_AREAS = [
        "Rawah", "Neota", "Comanche Peak", "Cache la Poudre"
    ]
    
    # Soil Types (subset of most common ones)
    SOIL_TYPES = [
        "C7745", "C7756", "C7711", "C7201", "C7702", "C7709", "C7717", "C7700",
        "C7746", "C7715", "C7710", "C7701", "C7704", "C7744", "C7703", "C7705",
        "C7713", "C7718", "C7712", "C7706", "C7707", "C7708", "C7714", "C7716",
        "C7719", "C7720", "C7721", "C7722", "C7723", "C7724", "C7725", "C7726",
        "C7727", "C7728", "C7729", "C7730", "C7731", "C7732", "C7733", "C7734"
    ]
    
    # Feature Ranges for Input Validation
    FEATURE_RANGES = {
        "elevation": (0, 5000),
        "aspect": (0, 360),
        "slope": (0, 90),
        "horizontal_distance_to_hydrology": (0, 2000),
        "vertical_distance_to_hydrology": (-1000, 1000),
        "horizontal_distance_to_roadways": (0, 7000),
        "hillshade_9am": (0, 255),
        "hillshade_noon": (0, 255),
        "hillshade_3pm": (0, 255),
        "horizontal_distance_to_fire_points": (0, 10000)
    }
    
    @classmethod
    def get_api_config(cls) -> Dict[str, str]:
        """Get API configuration"""
        return {
            "inference_api_url": cls.INFERENCE_API_URL,
            "mlflow_url": cls.MLFLOW_URL
        }
    
    @classmethod
    def get_feature_config(cls) -> Dict[str, Any]:
        """Get feature configuration"""
        return {
            "numeric_features": cls.NUMERIC_FEATURES,
            "categorical_features": cls.CATEGORICAL_FEATURES,
            "cover_types": cls.COVER_TYPES,
            "wilderness_areas": cls.WILDERNESS_AREAS,
            "soil_types": cls.SOIL_TYPES,
            "feature_ranges": cls.FEATURE_RANGES
        }
