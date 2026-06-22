"""
OCR service layer. Has no knowledge of FastAPI/HTTP — it accepts raw file bytes
and returns a structured result. This allows the same logic to be reused in both
the synchronous HTTP endpoint and the background Celery worker without duplication.
"""
from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass
from typing import List

import pytesseract
from PIL import Image, ImageOps
from pdf2image import convert_from_bytes

from app.core.exceptions import OCRProcessingError, PDFTooLargeForSyncError
from app.schemas.ocr import PageResult

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    pages: List[PageResult]
    total_pages: int
    processing_time_ms: float


def _preprocess_image(image: Image.Image) -> Image.Image:
    """Light preprocessing to improve Tesseract accuracy:
    convert to grayscale and auto-equalize contrast.
    Avoids aggressive transformations that tend to hurt text with varied backgrounds."""
    grayscale = ImageOps.grayscale(image)
    return ImageOps.autocontrast(grayscale)


def _run_tesseract_on_image(image: Image.Image, languages: str) -> tuple[str, float, int]:
    """Return (text, mean_confidence, word_count) for a single image."""
    processed = _preprocess_image(image)

    try:
        data = pytesseract.image_to_data(
            processed, lang=languages, output_type=pytesseract.Output.DICT
        )
    except pytesseract.TesseractError as exc:
        raise OCRProcessingError(str(exc)) from exc

    words = []
    confidences = []
    for i, word in enumerate(data["text"]):
        word = word.strip()
        if not word:
            continue
        words.append(word)
        conf = data["conf"][i]
        try:
            conf_value = float(conf)
        except (TypeError, ValueError):
            conf_value = -1.0
        if conf_value >= 0:
            confidences.append(conf_value)

    text = " ".join(words)
    mean_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
    return text, mean_confidence, len(words)


def extract_text_from_image(file_bytes: bytes, languages: str) -> OCRResult:
    """OCR for a single image (PNG/JPEG/WebP/BMP/TIFF)."""
    start = time.perf_counter()
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.load()
    except Exception as exc:  # noqa: BLE001
        raise OCRProcessingError(f"Could not open image: {exc}") from exc

    text, confidence, word_count = _run_tesseract_on_image(image, languages)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    page = PageResult(page_number=1, text=text, mean_confidence=confidence, word_count=word_count)
    logger.info("OCR image done in %.2fms, words=%d, confidence=%.2f", elapsed_ms, word_count, confidence)

    return OCRResult(pages=[page], total_pages=1, processing_time_ms=elapsed_ms)


def extract_text_from_pdf(
    file_bytes: bytes,
    languages: str,
    *,
    max_pages: int | None = None,
    dpi: int = 200,
) -> OCRResult:
    """OCR for PDF: render each page to an image via pdf2image (poppler),
    then run the same pipeline as for regular images.

    max_pages: if set and the PDF has more pages, raises PDFTooLargeForSyncError
    (used by the sync endpoint to avoid hanging HTTP requests for minutes).
    """
    start = time.perf_counter()
    try:
        images = convert_from_bytes(file_bytes, dpi=dpi)
    except Exception as exc:  # noqa: BLE001
        raise OCRProcessingError(f"Could not render PDF: {exc}") from exc

    if max_pages is not None and len(images) > max_pages:
        raise PDFTooLargeForSyncError(max_pages)

    pages: List[PageResult] = []
    for idx, image in enumerate(images, start=1):
        text, confidence, word_count = _run_tesseract_on_image(image, languages)
        pages.append(
            PageResult(page_number=idx, text=text, mean_confidence=confidence, word_count=word_count)
        )

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info("OCR PDF done in %.2fms, pages=%d", elapsed_ms, len(pages))

    return OCRResult(pages=pages, total_pages=len(pages), processing_time_ms=elapsed_ms)


def is_tesseract_available() -> bool:
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # noqa: BLE001
        return False
