def test_ocr_sync_recognizes_text_in_image(client, auth_headers, sample_text_image_bytes):
    files = {"file": ("hello.png", sample_text_image_bytes, "image/png")}
    response = client.post("/api/v1/ocr/sync", files=files, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()

    assert body["total_pages"] == 1
    assert len(body["pages"]) == 1

    recognized_text = body["pages"][0]["text"].upper()
    # We don't require 100% OCR accuracy — just that the key words are recognized
    assert "HELLO" in recognized_text
    assert "WORLD" in recognized_text
    assert body["pages"][0]["mean_confidence"] > 0


def test_ocr_sync_recognizes_multi_page_pdf(client, auth_headers, sample_pdf_bytes):
    files = {"file": ("doc.pdf", sample_pdf_bytes, "application/pdf")}
    response = client.post("/api/v1/ocr/sync", files=files, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()

    assert body["total_pages"] == 2
    assert "PAGE" in body["pages"][0]["text"].upper()
    assert "ONE" in body["pages"][0]["text"].upper()
    assert "TWO" in body["pages"][1]["text"].upper()


def test_ocr_sync_rejects_unsupported_file_type(client, auth_headers):
    files = {"file": ("data.txt", b"just some text", "text/plain")}
    response = client.post("/api/v1/ocr/sync", files=files, headers=auth_headers)

    assert response.status_code == 415
    assert "Unsupported file type" in response.json()["detail"]


def test_ocr_sync_rejects_corrupted_image(client, auth_headers):
    files = {"file": ("broken.png", b"not-a-real-image", "image/png")}
    response = client.post("/api/v1/ocr/sync", files=files, headers=auth_headers)

    assert response.status_code == 422
