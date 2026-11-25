import hmac
import logging
import os
import sqlite3
from datetime import UTC, datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
import httpx
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

logger = logging.getLogger("google_reviews_ai_bot")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Google Maps Reviews AI Bot",
    description="Sincroniza reseñas de Google Business Profile, genera respuestas con OpenAI en el idioma del cliente y las publica vía API oficial.",
    version="1.0.0",
)

GBP_SCOPE = "https://www.googleapis.com/auth/business.manage"


def get_settings() -> dict:
    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "api_secret": os.getenv("API_SECRET", ""),
        "google_token_file": os.getenv("GOOGLE_TOKEN_FILE", "token.json"),
        "account_id": os.getenv("GOOGLE_BUSINESS_ACCOUNT_ID", ""),
        "location_id": os.getenv("GOOGLE_BUSINESS_LOCATION_ID", ""),
        "business_name": os.getenv("BUSINESS_NAME", "Nuestro Negocio"),
        "database_path": os.getenv("DATABASE_PATH", "reviews.db"),
    }


STAR_MAP = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}


class ReviewDraftRequest(BaseModel):
    business_name: str = Field(min_length=1, max_length=120)
    reviewer_name: str = Field(min_length=1, max_length=120)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2000)


def init_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS replied_reviews (
                review_id TEXT PRIMARY KEY,
                reviewer_name TEXT NOT NULL,
                rating INTEGER NOT NULL,
                reply_text TEXT NOT NULL,
                replied_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def is_review_replied(db_path: str, review_id: str) -> bool:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM replied_reviews WHERE review_id = ?", (review_id,)
        ).fetchone()
    return row is not None


def mark_review_replied(
    db_path: str, review_id: str, reviewer_name: str, rating: int, reply_text: str
) -> None:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO replied_reviews (review_id, reviewer_name, rating, reply_text, replied_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (review_id, reviewer_name, rating, reply_text, datetime.now(UTC).isoformat()),
        )
        conn.commit()


def get_google_access_token(settings: dict) -> str:
    token_file = settings["google_token_file"]
    if not os.path.exists(token_file):
        raise HTTPException(
            status_code=500,
            detail=f"OAuth token file not found: {token_file}",
        )
    creds = Credentials.from_authorized_user_file(token_file, scopes=[GBP_SCOPE])
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
        with open(token_file, "w", encoding="utf-8") as fh:
            fh.write(creds.to_json())
    return creds.token


def generate_review_reply(
    business_name: str, reviewer_name: str, rating: int, comment: str, settings: dict
) -> str:
    if not settings["openai_api_key"]:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=settings["openai_api_key"], timeout=15.0)
    prompt = (
        f"Business: {business_name}\n"
        f"Reviewer: {reviewer_name}\n"
        f"Rating: {rating}/5\n"
        f"Comment: {comment or '(no written comment)'}\n\n"
        "Write a concise, polite, authentic public owner reply in the same language as the review "
        "(default to English if no comment and business name is English, or Spanish if Spanish). "
        "Do not invent discounts or promises."
    )
    resp = client.chat.completions.create(
        model=settings["openai_model"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    content = (resp.choices[0].message.content or "").strip()
    if not content:
        raise HTTPException(status_code=502, detail="Empty response from OpenAI")
    return content


def fetch_google_reviews(settings: dict) -> list[dict]:
    if not settings["account_id"] or not settings["location_id"]:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_BUSINESS_ACCOUNT_ID and GOOGLE_BUSINESS_LOCATION_ID are required",
        )
    token = get_google_access_token(settings)
    url = (
        f"https://mybusiness.googleapis.com/v4/accounts/{settings['account_id']}"
        f"/locations/{settings['location_id']}/reviews"
    )
    resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15.0)
    resp.raise_for_status()
    return resp.json().get("reviews", [])


def publish_google_reply(review_id: str, reply_text: str, settings: dict) -> dict:
    token = get_google_access_token(settings)
    url = (
        f"https://mybusiness.googleapis.com/v4/accounts/{settings['account_id']}"
        f"/locations/{settings['location_id']}/reviews/{review_id}/reply"
    )
    resp = httpx.put(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"comment": reply_text},
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()


def sync_and_reply_all(settings: dict) -> dict:
    reviews = fetch_google_reviews(settings)
    replied = []
    skipped = 0

    for item in reviews:
        review_id = item.get("reviewId") or item.get("name", "").split("/")[-1]
        if not review_id or item.get("reviewReply") or is_review_replied(settings["database_path"], review_id):
            skipped += 1
            continue

        reviewer = item.get("reviewer", {}).get("displayName", "Cliente")
        rating = STAR_MAP.get(item.get("starRating", "FIVE"), 5)
        comment = item.get("comment", "")

        reply_text = generate_review_reply(
            settings["business_name"], reviewer, rating, comment, settings
        )
        publish_google_reply(review_id, reply_text, settings)
        mark_review_replied(settings["database_path"], review_id, reviewer, rating, reply_text)
        replied.append({"review_id": review_id, "reviewer": reviewer, "rating": rating, "reply": reply_text})

    return {"replied_count": len(replied), "skipped_count": skipped, "replied": replied}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reviews/draft")
def draft_reply(review: ReviewDraftRequest):
    """Genera el borrador de respuesta con IA para una reseña puntual."""
    settings = get_settings()
    reply_text = generate_review_reply(
        review.business_name, review.reviewer_name, review.rating, review.comment, settings
    )
    return {
        "business": review.business_name,
        "reviewer": review.reviewer_name,
        "rating": review.rating,
        "generated_reply": reply_text,
    }


@app.post("/reviews/sync-and-reply")
def sync_reviews(x_api_secret: Optional[str] = Header(None, alias="X-Api-Secret")):
    """Obtiene reseñas sin responder de Google Business Profile, genera respuesta y la publica."""
    settings = get_settings()
    if settings["api_secret"]:
        if not x_api_secret or not hmac.compare_digest(x_api_secret, settings["api_secret"]):
            raise HTTPException(status_code=403, detail="Invalid API secret")
    return sync_and_reply_all(settings)
