def test_health_check_returns_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["app_name"] == "OCRGateway"
    # Tesseract must be available in the test environment (same as the Docker image)
    assert body["tesseract_available"] is True


def test_root_returns_useful_info(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "docs" in response.json()
