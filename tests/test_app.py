import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import unittest.mock as mock

with mock.patch.dict(os.environ, {"MLFLOW_TRACKING_URI": "http://localhost:5000"}):
    with mock.patch("mlflow.set_tracking_uri"), mock.patch("mlflow.set_experiment"):
        from app import app as flask_app

@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c

def test_health(client):
    with mock.patch("mlflow.set_tracking_uri"), mock.patch("mlflow.set_experiment"):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "healthy"

def test_info(client):
    r = client.get("/api/info")
    assert r.status_code == 200
    data = r.get_json()
    assert "version" in data
    assert "app" in data

def test_predict(client):
    with mock.patch("mlflow.start_run") as mock_run:
        mock_run.return_value.__enter__ = mock.Mock(return_value=mock.MagicMock())
        mock_run.return_value.__exit__ = mock.Mock(return_value=False)
        with mock.patch("mlflow.log_param"), mock.patch("mlflow.log_metric"), mock.patch("mlflow.set_tag"):
            r = client.post("/api/predict", json={"input": 10})
            assert r.status_code == 200
            data = r.get_json()
            assert "result" in data
            assert data["result"] == 25.0
