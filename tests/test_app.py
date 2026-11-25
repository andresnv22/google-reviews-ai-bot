from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

import app as reviews_app

client = TestClient(reviews_app.app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_sync_rejects_invalid_secret(monkeypatch):
    monkeypatch.setenv("API_SECRET", "my-secret")
    res = client.post("/reviews/sync-and-reply", headers={"X-Api-Secret": "wrong"})
    assert res.status_code == 403


def test_sync_and_reply_skips_already_replied(tmp_path, monkeypatch):
    monkeypatch.setenv("API_SECRET", "my-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GOOGLE_BUSINESS_ACCOUNT_ID", "acc-1")
    monkeypatch.setenv("GOOGLE_BUSINESS_LOCATION_ID", "loc-1")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "reviews.db"))

    fake_reviews = [
        {
            "reviewId": "rev-1",
            "reviewer": {"displayName": "Mateo"},
            "starRating": "FIVE",
            "comment": "Excelente servicio!",
        },
        {
            "reviewId": "rev-2",
            "reviewer": {"displayName": "Sarah"},
            "starRating": "FOUR",
            "comment": "Great food",
            "reviewReply": {"comment": "Already replied"},
        },
    ]

    mock_ai_resp = MagicMock(choices=[MagicMock(message=MagicMock(content="¡Gracias Mateo!"))])

    with (
        patch("app.get_google_access_token", return_value="fake-token"),
        patch("app.httpx.get") as mock_get,
        patch("app.httpx.put") as mock_put,
        patch("app.OpenAI") as mock_openai,
    ):
        mock_get.return_value.json.return_value = {"reviews": fake_reviews}
        mock_get.return_value.raise_for_status.return_value = None
        mock_put.return_value.json.return_value = {"comment": "¡Gracias Mateo!"}
        mock_put.return_value.raise_for_status.return_value = None
        mock_openai.return_value.chat.completions.create.return_value = mock_ai_resp

        r1 = client.post("/reviews/sync-and-reply", headers={"X-Api-Secret": "my-secret"})
        r2 = client.post("/reviews/sync-and-reply", headers={"X-Api-Secret": "my-secret"})

    assert r1.status_code == 200
    assert r1.json()["replied_count"] == 1
    assert r1.json()["skipped_count"] == 1
    assert r2.status_code == 200
    assert r2.json()["replied_count"] == 0
    assert r2.json()["skipped_count"] == 2
    mock_put.assert_called_once()
