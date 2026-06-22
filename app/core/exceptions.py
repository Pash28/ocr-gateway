"""Domain exceptions. Caught in main.py via exception handlers
to return clean JSON responses to the client instead of stack traces."""


class OCRGatewayError(Exception):
    """Base application exception."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class UnsupportedFileTypeError(OCRGatewayError):
    def __init__(self, content_type: str):
        super().__init__(
            f"Unsupported file type: '{content_type}'. Allowed: images (png/jpeg/webp/bmp/tiff) or application/pdf.",
            status_code=415,
        )


class FileTooLargeError(OCRGatewayError):
    def __init__(self, max_mb: int):
        super().__init__(f"File exceeds the maximum allowed size of {max_mb} MB.", status_code=413)


class PDFTooLargeForSyncError(OCRGatewayError):
    def __init__(self, max_pages: int):
        super().__init__(
            f"PDF has more than {max_pages} pages. Use the /ocr/async endpoint for larger documents.",
            status_code=413,
        )


class OCRProcessingError(OCRGatewayError):
    def __init__(self, detail: str):
        super().__init__(f"OCR processing failed: {detail}", status_code=422)


class JobNotFoundError(OCRGatewayError):
    def __init__(self, job_id: str):
        super().__init__(f"Job '{job_id}' not found.", status_code=404)
