import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_redis():
    """Patch redis.Redis for every test — no live Redis required."""
    with patch("redis.Redis") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.ping.return_value = True
        mock_cls.return_value = mock_instance
        # Re-import app after patching so it picks up the mock
        import importlib
        import api.main as main_module
        importlib.reload(main_module)
        yield mock_instance


@pytest.fixture()
def client(mock_redis):
    from api.main import app
    return TestClient(app)


def test_health_returns_ok(client, mock_redis):
    mock_redis.ping.return_value = True
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_job_returns_job_id(client, mock_redis):
    mock_redis.hset.return_value = 1
    mock_redis.lpush.return_value = 1
    resp = client.post("/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert len(data["job_id"]) == 36  # UUID4 length


def test_get_existing_job_returns_status(client, mock_redis):
    mock_redis.hget.return_value = "queued"
    resp = client.get("/jobs/some-valid-id")
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"
    assert resp.json()["job_id"] == "some-valid-id"


def test_get_missing_job_returns_404(client, mock_redis):
    mock_redis.hget.return_value = None
    resp = client.get("/jobs/nonexistent-id")
    assert resp.status_code == 404


def test_health_when_redis_down(client, mock_redis):
    import redis as redis_lib
    mock_redis.ping.side_effect = redis_lib.exceptions.ConnectionError("down")
    resp = client.get("/health")
    assert resp.status_code == 503
