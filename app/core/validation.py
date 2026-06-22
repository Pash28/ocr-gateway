"""Shared file upload validation, reused by both OCR endpoints."""
from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import FileTooLargeError, UnsupportedFileTypeError


async def validate_and_read_upload(file: UploadFile, settings: Settings) -> tuple[bytes, str]:
    """Validate file type and size, return (content, content_type).

    Size is checked against actual bytes read, not the Content-Length header,
    since clients may omit it or provide an incorrect value.
    """
    content_type = file.content_type or ""
    allowed_types = set(settings.allowed_image_types) | {settings.allowed_pdf_type}

    if content_type not in allowed_types:
        raise UnsupportedFileTypeError(content_type)

    file_bytes = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise FileTooLargeError(settings.max_upload_size_mb)

    return file_bytes, content_type
