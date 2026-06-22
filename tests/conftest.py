import io
import os

import pytest

os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("API_KEY_ENABLED", "true")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.main import app

API_KEY = "test-api-key"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict:
    return {"X-API-Key": API_KEY}


def _render_text_image(text: str, size=(600, 150)) -> Image.Image:
    image = Image.new("RGB", size, color="white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    draw.text((20, 50), text, fill="black", font=font)
    return image


@pytest.fixture
def sample_text_image_bytes() -> bytes:
    """PNG with large, clear text — Tesseract should recognize it with near-zero errors."""
    image = _render_text_image("HELLO WORLD")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Two-page PDF assembled from two text images via Pillow."""
    page1 = _render_text_image("PAGE ONE")
    page2 = _render_text_image("PAGE TWO")
    buf = io.BytesIO()
    page1.save(buf, format="PDF", save_all=True, append_images=[page2])
    return buf.getvalue()
