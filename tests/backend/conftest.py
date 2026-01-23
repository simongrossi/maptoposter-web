import pytest
from fastapi.testclient import TestClient
from backend.main import app
from unittest.mock import MagicMock

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_celery_task(mocker):
    """Mock the Celery task delay method to prevent running actual worker logic."""
    mock_task = mocker.patch("backend.main.generate_poster_task")
    mock_delay = MagicMock()
    # Simulate a Task ID
    mock_delay.id = "mock-task-id-123"
    mock_task.delay.return_value = mock_delay
    return mock_task
