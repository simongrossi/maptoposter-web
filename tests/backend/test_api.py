import pytest


BASE_PAYLOAD = {
    "city": "TestCity",
    "country": "TestCountry",
    "style": "noir",
    "distance": 5000,
    "width": 12.0,
    "height": 16.0,
    "format": "png",
    "custom_layers": [],
}


def test_generate_endpoint(client, mock_celery_task):
    """POST /generate enqueue une tache et renvoie son identifiant."""
    response = client.post("/generate", json=BASE_PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "123e4567-e89b-12d3-a456-426614174000"
    mock_celery_task.assert_called_once()
    kwargs = mock_celery_task.call_args.kwargs
    assert kwargs["args"][0]["city"] == "TestCity"
    assert kwargs["kwargs"]["session_id"]

    # Une session anonyme signee doit avoir ete emise.
    cookie = client.cookies.get("mp_session")
    assert cookie
    assert cookie.count(".") == 2


def test_themes_endpoint(client):
    """GET /themes renvoie les themes du repertoire themes/."""
    response = client.get("/themes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("themes"), list)
    assert data["themes"], "au moins un theme doit etre present"


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_invalid_payload(client):
    """Un champ obligatoire manquant doit produire une 422."""
    response = client.post("/generate", json={"city": "TestCity"})
    assert response.status_code == 422


@pytest.mark.parametrize(
    "override",
    [
        {"style": "../../etc/passwd"},
        {"style": "noir/../../secret"},
        {"distance": 25001},
        {"distance": 999},
        {"format": "exe"},
        {"width": 40, "height": 40, "dpi": 600},
        {"dpi": 601},
        {"city": "x" * 121},
        {"paper_size": "bad/../../size"},
        {"custom_layers": [{"label": "x", "tags": {"a": "b"}, "color": "red"}]},
        {
            "custom_layers": [
                {"label": "x", "tags": {"a": 'b"];out;'}, "color": "#ffffff"}
            ]
        },
    ],
)
def test_generate_rejects_invalid_values(client, override):
    payload = {**BASE_PAYLOAD, **override}
    response = client.post("/generate", json=payload)
    assert response.status_code == 422


def test_generate_rejects_extra_fields(client):
    response = client.post("/generate", json={**BASE_PAYLOAD, "is_admin": True})
    assert response.status_code == 422


def test_task_is_not_visible_to_another_session(client, mock_celery_task):
    response = client.post("/generate", json=BASE_PAYLOAD)
    task_id = response.json()["task_id"]

    from fastapi.testclient import TestClient
    from backend.main import app

    other = TestClient(app)
    response = other.get(f"/tasks/{task_id}")
    assert response.status_code == 404


def test_unknown_task_is_hidden(client):
    response = client.get("/tasks/123e4567-e89b-12d3-a456-426614174999")
    assert response.status_code == 404


def test_invalid_signed_download(client):
    response = client.get(
        "/download/paris.png?expires=4000000000&signature=" + "0" * 64
    )
    assert response.status_code == 403


def test_expired_signed_download(client):
    response = client.get("/download/paris.png?expires=1&signature=" + "0" * 64)
    assert response.status_code == 403


def test_download_path_traversal_rejected(client):
    response = client.get("/download/..%2F..%2Fetc%2Fpasswd")
    assert response.status_code in {403, 404}


def test_history_is_scoped_to_session(client, fake_redis):
    response = client.get("/history")
    assert response.status_code == 200
    assert response.json() == []


def test_active_slot_release_is_idempotent(fake_redis):
    from backend.redis_client import release_active_slot

    fake_redis.set("active:test-session", 1)
    release_active_slot(fake_redis, "task-1", "test-session")
    release_active_slot(fake_redis, "task-1", "test-session")
    assert fake_redis.get("active:test-session") is None


def test_city_is_reconstructed_from_object_key():
    from backend.main import _city_from_key

    assert _city_from_key("new_york_noir_0123456789ab.png") == "New York"
    assert _city_from_key("paris_feature_based_0123456789ab.png") == "Paris"
    assert _city_from_key("paris_ALL_THEMES_0123456789ab.zip") == "Paris"
