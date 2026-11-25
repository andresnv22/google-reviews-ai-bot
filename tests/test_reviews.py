from fastapi.testclient import TestClient

from app import app


def test_review_is_draft_even_outside_demo(monkeypatch):
    monkeypatch.setattr("app.DEMO_MODE", False)
    client = TestClient(app)
    response = client.post(
        "/reviews/reply",
        json={"business_name": "Example", "reviewer_name": "Ana", "rating": 5, "comment": "Bien"},
    )
    assert response.status_code == 200
    assert response.json()["published"] is False


def test_invalid_rating_rejected():
    client = TestClient(app)
    response = client.post(
        "/reviews/reply",
        json={"reviewer_name": "Ana", "rating": 6, "comment": "Bien"},
    )
    assert response.status_code == 422
