"""
Pytest configuration and fixtures

Shared fixtures for tests:
- API client
- Database connections
- Sample data
- Mock models
"""

import pytest
import pandas as pd
from typing import Dict, List

# TODO: Add imports for test utilities


@pytest.fixture
def sample_patient_data() -> Dict:
    """
    Fixture: Sample patient data for testing
    
    Returns:
        dict: Patient data dictionary
    """
    # TODO: Implement
    # return {
    #     "age": 65,
    #     "gender": "Male",
    #     "admission_type": "Emergency",
    #     ...
    # }
    pass


@pytest.fixture
def sample_batch_data() -> List[Dict]:
    """
    Fixture: Sample batch of patients for testing
    
    Returns:
        list: List of patient dictionaries
    """
    # TODO: Implement
    pass


@pytest.fixture
def api_client():
    """
    Fixture: API client for testing
    
    Returns:
        Client: Test client for API
    """
    # TODO: Implement
    # from fastapi.testclient import TestClient
    # from services.api.main import app
    # return TestClient(app)
    pass


@pytest.fixture
def db_connection():
    """
    Fixture: Database connection for testing
    
    Returns:
        Connection: Test database connection
    """
    # TODO: Implement
    pass


@pytest.fixture
def mock_mlflow_model():
    """
    Fixture: Mock MLflow model for testing
    
    Returns:
        Model: Mock model object
    """
    # TODO: Implement
    pass


# TODO: Add more fixtures as needed
