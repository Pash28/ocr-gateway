# OCRGateway

REST API for text recognition (OCR) from images and PDFs. Built with **FastAPI** + **Tesseract OCR** + **Celery** + **Redis**. Docker-ready with CI/CD via GitHub Actions.

![CI](https://github.com/YOUR_USERNAME/ocr-gateway/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## Features

- **Synchronous OCR** — instant response for images and short PDFs (≤ 3 pages by default)
- **Asynchronous OCR** — queues the task via Celery, returns a `job_id`, result fetched later (for large PDFs)
- **Supported formats**: PNG, JPEG, WebP, BMP, TIFF, PDF (multi-page)
- **Multi-language**: English, Russian, and any other Tesseract language via the `languages` parameter
- **Confidence score** — mean OCR confidence per page
- **API key authentication** via `X-API-Key` header
- **Rate limiting**: 30 requests/minute by default (configurable)
- **Swagger UI** at `/docs`, ReDoc at `/redoc`

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.111 |
| OCR engine | Tesseract 5 (pytesseract) |
| PDF → images | pdf2image + Poppler |
| Background tasks | Celery 5 |
| Broker / job store | Redis 7 |
| Rate limiting | slowapi |
| Configuration | pydantic-settings (.env) |
| Tests | pytest + httpx + fakeredis |
| Linter | ruff |
| Containers | Docker + docker-compose |
| CI/CD | GitHub Actions → Render |

---

## Project Structure

```
ocr-gateway/
├── app/
│   ├── core/
│   │   ├── config.py         # Settings via pydantic-settings + .env
│   │   ├── exceptions.py     # Domain exceptions → clean JSON responses
│   │   ├── logging.py        # Unified logging setup
│   │   ├── rate_limit.py     # Shared Limiter instance (slowapi)
│   │   ├── security.py       # X-API-Key verification
│   │   └── validation.py     # File upload validation
│   ├── routers/
│   │   ├── health.py         # GET /api/v1/health
│   │   └── ocr.py            # POST /sync, POST /async, GET /jobs/{id}
│   ├── schemas/
│   │   └── ocr.py            # Pydantic request/response schemas
│   ├── services/
│   │   ├── ocr_service.py    # Core OCR logic (Tesseract)
│   │   └── job_store.py      # Async job CRUD (Redis)
│   ├── workers/
│   │   ├── celery_app.py     # Celery initialization
│   │   └── ocr_tasks.py      # process_file_task
│   └── main.py               # FastAPI entry point
├── tests/
│   ├── conftest.py           # Fixtures: client, sample files
│   ├── test_auth.py
│   ├── test_health.py
│   ├── test_job_store.py
│   └── test_ocr_sync.py
├── .github/workflows/ci.yml  # GitHub Actions CI/CD
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

---

## Quick Start

### Option 1 — Docker (recommended)

```bash
git clone https://github.com/YOUR_USERNAME/ocr-gateway.git
cd ocr-gateway

cp .env.example .env
# Edit .env and set your API_KEY

docker compose up --build
```

Service available at `http://localhost:8000`

### Option 2 — Local (without Docker)

Requirements: Python 3.12+, Tesseract 5, Poppler

```bash
# macOS
brew install tesseract tesseract-lang poppler

# Ubuntu / Debian
sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus poppler-utils

# Python setup
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env

# Start the API
uvicorn app.main:app --reload

# Start the Celery worker (separate terminal)
celery -A app.workers.celery_app worker --loglevel=info
```

---

## API Reference

### Authentication

All OCR endpoints require the following header:
```
X-API-Key: your-secret-key
```

### Synchronous OCR

```bash
curl -X POST http://localhost:8000/api/v1/ocr/sync \
  -H "X-API-Key: dev-secret-key" \
  -F "file=@document.png" \
  -F "languages=eng"
```

**Response:**
```json
{
  "filename": "document.png",
  "content_type": "image/png",
  "languages": "eng",
  "total_pages": 1,
  "processing_time_ms": 342.5,
  "pages": [
    {
      "page_number": 1,
      "text": "Hello, World! This is OCR.",
      "mean_confidence": 94.7,
      "word_count": 5
    }
  ]
}
```

### Asynchronous OCR (large PDFs)

```bash
# Step 1 — queue the job
curl -X POST http://localhost:8000/api/v1/ocr/async \
  -H "X-API-Key: dev-secret-key" \
  -F "file=@large_document.pdf" \
  -F "languages=eng+rus"
```

```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "pending",
  "status_url": "/api/v1/ocr/jobs/3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "created_at": "2024-01-15T12:00:00Z"
}
```

```bash
# Step 2 — poll for the result
curl http://localhost:8000/api/v1/ocr/jobs/3fa85f64-5717-4562-b3fc-2c963f66afa6 \
  -H "X-API-Key: dev-secret-key"
```

The `status` field progresses: `pending → processing → completed` (or `failed`).

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

```json
{
  "status": "ok",
  "app_name": "OCRGateway",
  "environment": "docker",
  "tesseract_available": true,
  "redis_available": true
}
```

---

## Tests

```bash
# Run all tests
pytest tests/ -v

# With coverage report
pip install pytest-cov
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## Deploy to Render

1. Create a new **Web Service** on [render.com](https://render.com) and connect your repository
2. Set **Environment** to **Docker**
3. Add environment variables in Render Dashboard:
   ```
   API_KEY=your-production-secret
   REDIS_URL=<Internal URL from your Render Redis instance>
   ENVIRONMENT=production
   DEBUG=false
   ```
4. Create a **Redis** instance on Render, copy its Internal URL to `REDIS_URL`
5. For CI/CD auto-deploy: copy the **Deploy Hook URL** from Render → Service → Settings, then add it as a GitHub Actions secret named `RENDER_DEPLOY_HOOK_URL`

Every push to `main` will then trigger: lint → tests → Docker build → deploy to Render.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `API_KEY` | `dev-secret-key` | Secret for the X-API-Key header |
| `API_KEY_ENABLED` | `true` | Enable/disable authentication |
| `DEFAULT_LANGUAGES` | `eng` | Default Tesseract language(s) |
| `MAX_UPLOAD_SIZE_MB` | `20` | Maximum file size |
| `MAX_PDF_PAGES_SYNC` | `3` | Page limit for /sync endpoint |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `RATE_LIMIT_PER_MINUTE` | `30` | Rate limit per IP |
| `DEBUG` | `false` | Enable verbose logging |

---

## License

MIT
