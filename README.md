# Google Maps Reviews AI Bot

Bot en Python (FastAPI) para negocios locales (clínicas, restaurantes, hoteles, talleres) que responde reseñas de Google Maps automáticamente con IA según la calificación y el comentario del cliente.

## Instalación rápida
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --reload --port 8002
```

## Probar en modo demo
```bash
curl -X POST http://127.0.0.1:8002/reviews/reply \
  -H "Content-Type: application/json" \
  -d '{"business_name": "Restaurante El Roble", "reviewer_name": "Mateo", "rating": 5, "comment": "Excelente comida y atención"}'
```
