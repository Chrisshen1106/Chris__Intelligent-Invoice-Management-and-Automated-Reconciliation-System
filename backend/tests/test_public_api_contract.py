import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from services.system import public_service


PUBLIC_API_NAME = (
    "\u667a\u6167\u767c\u7968\u7ba1\u7406\u8207\u81ea\u52d5\u5c0d\u5e33\u7cfb\u7d71 / "
    "Intelligent Invoice Management and Automated Reconciliation System"
)


@pytest.mark.asyncio
async def test_public_api_metadata_is_available_without_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/public")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == PUBLIC_API_NAME
    assert body["baseUrl"] == "/api/public"
    assert body["docsUrl"] == "/api/public/docs"
    assert body["healthCheckUrl"] == "/api/public/health"
    assert body["authentication"] == "none"
    assert body["dataPolicy"] == {
        "persistsData": False,
        "readsPrivateDocuments": False,
    }
    assert {
        "method": "GET",
        "path": "/api/public",
        "description": "Public API metadata.",
        "status": "available",
    } in body["endpoints"]
    assert {
        "method": "GET",
        "path": "/api/public/health",
        "description": "Public API health check.",
        "status": "available",
    } in body["endpoints"]
    assert {
        "method": "POST",
        "path": "/api/public/ocr-demo",
        "description": "Public OCR demo returning only texts and tokens.",
        "status": "available",
    } in body["endpoints"]


@pytest.mark.asyncio
async def test_public_api_health_is_available_without_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/public/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["service"] == "public-api"
    assert body["status"] == "healthy"
    assert body["environment"]
    assert body["checkedAt"]
    assert body["checks"] == {
        "api": {
            "ok": True,
            "error": None,
        }
    }


@pytest.mark.asyncio
async def test_public_openapi_only_includes_public_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/public/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/api/public" in schema["paths"]
    assert "/api/public/health" in schema["paths"]
    assert "/api/public/ocr-demo" in schema["paths"]
    assert "/api/auth/login" not in schema["paths"]
    assert not any(path.startswith("/api/employee") for path in schema["paths"])
    assert schema["paths"]["/api/public"]["get"]["tags"] == ["Public API"]
    assert schema["paths"]["/api/public/health"]["get"]["tags"] == ["Public API"]
    assert schema["paths"]["/api/public/ocr-demo"]["post"]["tags"] == ["Public API"]


@pytest.mark.asyncio
async def test_public_openapi_supports_english_and_traditional_chinese():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        english_response = await client.get("/api/public/openapi.json?lang=en")
        chinese_response = await client.get("/api/public/openapi.json?lang=zh-TW")

    assert english_response.status_code == 200
    assert chinese_response.status_code == 200

    english_schema = english_response.json()
    chinese_schema = chinese_response.json()

    assert english_schema["info"]["title"] == "Intelligent Invoice Management and Automated Reconciliation System"
    assert english_schema["paths"]["/api/public"]["get"]["summary"] == "Public API metadata"
    assert english_schema["paths"]["/api/public/ocr-demo"]["post"]["summary"] == "Public OCR demo"
    assert "one page only" in english_schema["paths"]["/api/public/ocr-demo"]["post"]["description"]
    assert english_schema["paths"]["/api/public"]["get"]["responses"]["422"]["description"] == "Request validation failed."
    assert chinese_schema["info"]["title"] == "\u667a\u6167\u767c\u7968\u7ba1\u7406\u8207\u81ea\u52d5\u5c0d\u5e33\u7cfb\u7d71"
    assert chinese_schema["paths"]["/api/public"]["get"]["summary"] == "\u516c\u958b API \u4e2d\u7e7c\u8cc7\u6599"
    assert chinese_schema["paths"]["/api/public/ocr-demo"]["post"]["summary"] == "\u516c\u958b OCR \u9ad4\u9a57"
    assert "\u53ea\u8fa8\u8b58\u4e00\u9801" in chinese_schema["paths"]["/api/public/ocr-demo"]["post"]["description"]
    assert (
        chinese_schema["paths"]["/api/public"]["get"]["responses"]["422"]["description"]
        == "\u8acb\u6c42\u8cc7\u6599\u683c\u5f0f\u932f\u8aa4\uff0c\u6216\u5fc5\u8981\u6b04\u4f4d\u672a\u586b\u3002"
    )


@pytest.mark.asyncio
async def test_public_swagger_ui_is_available_without_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/public/docs")

    assert response.status_code == 200
    assert "/api/public/openapi.json" in response.text
    assert "public-docs-language" in response.text
    assert "zh-TW" in response.text
    assert "en" in response.text
    assert "Swagger UI" in response.text


@pytest.mark.asyncio
async def test_public_ocr_demo_returns_only_texts_and_tokens_without_auth(monkeypatch):
    def fake_run_ocr(file_bytes: bytes, content_type: str):
        assert file_bytes == b"fake image bytes"
        assert content_type == "image/png"
        return (
            "Invoice No AB12345678\nTotal 1000",
            [
                {
                    "text": "Invoice No",
                    "x": 10.0,
                    "y": 20.0,
                    "score": 0.99,
                },
                {
                    "text": "AB12345678",
                    "x": 110.0,
                    "y": 20.0,
                    "score": 0.98,
                },
            ],
        )

    monkeypatch.setattr(public_service, "run_ocr", fake_run_ocr)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/public/ocr-demo",
            files={"file": ("sample.png", b"fake image bytes", "image/png")},
        )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"texts", "tokens"}
    assert body["texts"] == ["Invoice No AB12345678", "Total 1000"]
    assert body["tokens"] == [
        {
            "text": "Invoice No",
            "x": 10.0,
            "y": 20.0,
            "score": 0.99,
        },
        {
            "text": "AB12345678",
            "x": 110.0,
            "y": 20.0,
            "score": 0.98,
        },
    ]
