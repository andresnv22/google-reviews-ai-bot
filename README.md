# Google Maps Reviews AI Bot

Bot en Python (FastAPI) para negocios locales que **genera borradores** de respuesta a reseñas con OpenAI. No consulta reseñas ni publica respuestas en Google Business Profile; una persona debe revisar y publicar cada borrador. Requiere `OPENAI_API_KEY`.

## Instalación rápida
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --reload --port 8002
```

## Probar el endpoint
```bash
curl -X POST http://127.0.0.1:8002/reviews/reply \
  -H "Content-Type: application/json" \
  -d '{"business_name": "Restaurante El Roble", "reviewer_name": "Mateo", "rating": 5, "comment": "Excelente comida y atención"}'
```
