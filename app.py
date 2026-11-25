import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(
    title="Google Maps Reviews AI Bot",
    description="Genera borradores de respuesta para reseñas; requiere revisión y publicación manual.",
    version="1.0.0",
)

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"


class ReviewPayload(BaseModel):
    business_name: str = "Clínica Dental Sonrisa"
    reviewer_name: str
    rating: int = Field(ge=1, le=5)
    comment: str


def generate_review_reply(review: ReviewPayload) -> str:
    """Genera una respuesta profesional y personalizada según las estrellas y comentario."""
    if DEMO_MODE or not os.getenv("OPENAI_API_KEY"):
        if review.rating >= 4:
            return (
                f"¡Muchas gracias, {review.reviewer_name}! Nos alegra muchísimo saber que tu "
                f"experiencia en {review.business_name} fue positiva. ¡Te esperamos pronto!"
            )
        if review.rating == 3:
            return (
                f"Hola {review.reviewer_name}, gracias por tu comentario sobre {review.business_name}. "
                "Tomamos muy en cuenta tus observaciones para seguir mejorando nuestro servicio."
            )
        return (
            f"Hola {review.reviewer_name}, lamentamos mucho que tu experiencia en {review.business_name} "
            "no haya sido la esperada. Escríbenos por interno para resolverlo de inmediato."
        )

    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
    return resp.choices[0].message.content or "Gracias por tu reseña."


@app.get("/health")
def health():
    return {"status": "ok", "demo_mode": DEMO_MODE}


@app.post("/reviews/reply")
def reply_to_review(review: ReviewPayload):
    """Genera un borrador. Este servicio no publica respuestas en Google."""
    reply_text = generate_review_reply(review)
    return {
        "business": review.business_name,
        "reviewer": review.reviewer_name,
        "rating": review.rating,
        "generated_reply": reply_text,
        "published": False,
        "demo_mode": DEMO_MODE,
    }
