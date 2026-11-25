from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_reply_to_review(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="¡Gracias Mateo por tu visita!"))]

    with patch("app.OpenAI") as mock_openai:
        mock_openai.return_value.chat.completions.create.return_value = mock_resp
        res = client.post(
            "/reviews/reply",
            json={
                "business_name": "Restaurante El Roble",
                "reviewer_name": "Mateo",
                "rating": 5,
                "comment": "Excelente comida",
            },
        )

    assert res.status_code == 200
    assert res.json()["generated_reply"] == "¡Gracias Mateo por tu visita!"


def test_reply_invalid_rating():
    res = client.post(
        "/reviews/reply",
        json={
            "business_name": "Restaurante El Roble",
            "reviewer_name": "Mateo",
            "rating": 6,
            "comment": "Excelente",
        },
    )
    assert res.status_code == 422
