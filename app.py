import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(
    title="Google Maps Reviews AI Bot",
    description="Genera respuestas personalizadas con IA para reseñas de Google Business Profile.",
    version="1.0.0",
)


class ReviewPayload(BaseModel):
    business_name: str
    reviewer_name: str
    rating: int = Field(ge=1, le=5)
    comment: str


def generate_review_reply(review: ReviewPayload) -> str:
    """Genera una respuesta profesional y personalizada usando OpenAI."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY no está configurada")

    client = OpenAI(api_key=api_key)
    prompt = (
        f"Negocio: {review.business_name}\n"
        f"Cliente: {review.reviewer_name}\n"
        f"Calificación: {review.rating}/5\n"
        f"Comentario: {review.comment}\n\n"
        "Redacta una respuesta corta, amable y profesional en español."
    )
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    content = resp.choices[0].message.content
    if not content:
        raise HTTPException(status_code=502, detail="Respuesta vacía de OpenAI")
    return content


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reviews/reply")
def reply_to_review(review: ReviewPayload):
    """Genera la respuesta personalizada para una reseña de Google Maps."""
    reply_text = generate_review_reply(review)
    return {
        "business": review.business_name,
        "reviewer": review.reviewer_name,
        "rating": review.rating,
        "generated_reply": reply_text,
    }
