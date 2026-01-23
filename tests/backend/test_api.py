def test_generate_endpoint(client, mock_celery_task):
    """Test POST /generate endpoint enqueues a task and returns ID."""
    payload = {
        "city": "TestCity",
        "country": "TestCountry",
        "style": "noir",
        "distance": 5000,
        "width": 12.0,
        "height": 16.0,
        "format": "png",
        "custom_layers": []
    }
    
    response = client.post("/generate", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["task_id"] == "mock-task-id-123"
    
    # Verify mock was called
    mock_celery_task.delay.assert_called_once()

def test_themes_endpoint(client):
    """Test GET /themes returns a list of themes."""
    # This relies on the actual 'themes' folder being present or mocked.
    # If the tests run in an env without themes folder, it might fail.
    # But usually the repo structure is kept.
    response = client.get("/themes")
    assert response.status_code == 200
    data = response.json()
    assert "themes" in data
    assert isinstance(data["themes"], list)

def test_generate_invalid_payload(client):
    """Test POST /generate validation."""
    # Missing country
    payload = {
        "city": "TestCity",
        # "country": "TestCountry", 
    }
    response = client.post("/generate", json=payload)
    assert response.status_code == 422 # FastAPI validation error
