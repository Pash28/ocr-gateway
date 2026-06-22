def test_ocr_sync_without_api_key_is_rejected(client, sample_text_image_bytes):
    files = {"file": ("test.png", sample_text_image_bytes, "image/png")}
    response = client.post("/api/v1/ocr/sync", files=files)
    assert response.status_code == 401


def test_ocr_sync_with_wrong_api_key_is_rejected(client, sample_text_image_bytes):
    files = {"file": ("test.png", sample_text_image_bytes, "image/png")}
    response = client.post(
        "/api/v1/ocr/sync", files=files, headers={"X-API-Key": "totally-wrong-key"}
    )
    assert response.status_code == 401
