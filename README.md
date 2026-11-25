# Google Maps Reviews AI Bot

Bot en Python (FastAPI) integrado con **Google Business Profile API** y **OpenAI** para obtener reseñas nuevas, generar respuestas personalizadas en el idioma del cliente y publicarlas automáticamente evitando duplicados con SQLite.

## Endpoints
- `POST /reviews/sync-and-reply`: consulta reseñas sin respuesta en Google Business Profile, genera respuesta con OpenAI y la publica con `PUT .../reply` (protegido por `X-Api-Secret`).
- `POST /reviews/draft`: genera únicamente el texto sugerido para una reseña enviada en el body.

## Instalación y uso
```bash
uv sync
cp .env.example .env
# Coloca token.json de Google OAuth2 (scope business.manage) y configura OPENAI_API_KEY
uv run uvicorn app:app --reload --port 8002
```

## Pruebas automatizadas
```bash
uv run pytest
```
