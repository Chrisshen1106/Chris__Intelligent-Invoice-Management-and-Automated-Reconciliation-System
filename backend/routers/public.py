import json

from fastapi import APIRouter, File, Query, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

from core.config import settings
from core.openapi import common_error_responses
from schemas.public import PublicApiHealthResponse, PublicApiInfoResponse, PublicOcrTextTokensResponse
from services.system.public_service import get_public_api_health, get_public_api_info, run_public_ocr_demo


PUBLIC_API_TAG = "Public API"
PUBLIC_API_PATHS = {"/api/public", "/api/public/health", "/api/public/ocr-demo"}
DEFAULT_PUBLIC_DOCS_LANGUAGE = "zh-TW"

router = APIRouter(prefix="/api/public", tags=[PUBLIC_API_TAG])


PUBLIC_OPENAPI_TEXT = {
    "en": {
        "title": "Intelligent Invoice Management and Automated Reconciliation System",
        "description": "Public demo API for the invoice management and reconciliation system.",
        "tag_description": "Public endpoints that do not require authentication.",
        "metadata_summary": "Public API metadata",
        "metadata_description": (
            "Return the public API catalog, documentation URL, authentication policy, "
            "and data handling policy. No authentication is required."
        ),
        "metadata_response": "Public API metadata.",
        "health_summary": "Public API health check",
        "health_description": (
            "Return a lightweight health check for the public API router. "
            "This endpoint does not check Supabase, OCR, Ollama, or private business data."
        ),
        "health_response": "Public API health status.",
        "ocr_summary": "Public OCR demo",
        "ocr_description": (
            "Upload a JPG, PNG, or PDF file and run OCR only. "
            "The response only includes merged text lines and OCR tokens. "
            "No LLM extraction is performed and no data is persisted. "
            "OCR recognizes one page only; accuracy is not guaranteed for files with more than one page."
        ),
        "ocr_response": "OCR texts and tokens.",
        "unsupported_media_type": "Only JPG, PNG, and PDF files are supported.",
        "validation_error": "Request validation failed.",
        "server_error": "Internal server error.",
        "language_label": "Language",
        "english_label": "English",
        "traditional_chinese_label": "Traditional Chinese",
    },
    "zh-TW": {
        "title": "智慧發票管理與自動對帳系統",
        "description": "發票管理與自動化對帳系統的公開展示 API。",
        "tag_description": "不需要登入即可呼叫的公開端點。",
        "metadata_summary": "公開 API 中繼資料",
        "metadata_description": "回傳公開 API 目錄、文件網址、驗證政策與資料處理政策。不需要登入。",
        "metadata_response": "公開 API 中繼資料。",
        "health_summary": "公開 API 健康檢查",
        "health_description": (
            "回傳 public router 的輕量健康檢查。"
            "此端點不檢查 Supabase、OCR、Ollama 或私有業務資料。"
        ),
        "health_response": "公開 API 健康狀態。",
        "ocr_summary": "公開 OCR 體驗",
        "ocr_description": (
            "上傳 JPG、PNG 或 PDF 檔案，只執行 OCR。"
            "回應只包含合併後的文字行與 OCR tokens。"
            "不會執行 LLM 欄位抽取，也不會保存資料。"
            "OCR 只辨識一頁，超過一頁不保證準確。"
        ),
        "ocr_response": "OCR 文字行與 tokens。",
        "unsupported_media_type": "只支援 JPG、PNG 與 PDF 檔案。",
        "validation_error": "請求資料格式錯誤，或必要欄位未填。",
        "server_error": "伺服器內部錯誤。",
        "language_label": "語言",
        "english_label": "English",
        "traditional_chinese_label": "繁體中文",
    },
}


def normalize_public_docs_language(language: str | None) -> str:
    if not language:
        return DEFAULT_PUBLIC_DOCS_LANGUAGE

    normalized = language.strip()
    aliases = {
        "zh": "zh-TW",
        "zh-tw": "zh-TW",
        "zh_tw": "zh-TW",
        "tw": "zh-TW",
        "en-us": "en",
        "en_us": "en",
    }
    return aliases.get(normalized.lower(), normalized if normalized in PUBLIC_OPENAPI_TEXT else DEFAULT_PUBLIC_DOCS_LANGUAGE)


def apply_public_openapi_language(schema: dict, language: str) -> dict:
    text = PUBLIC_OPENAPI_TEXT[language]
    schema["info"]["title"] = text["title"]
    schema["info"]["description"] = text["description"]
    schema["tags"] = [{"name": PUBLIC_API_TAG, "description": text["tag_description"]}]

    metadata_operation = schema["paths"]["/api/public"]["get"]
    metadata_operation["summary"] = text["metadata_summary"]
    metadata_operation["description"] = text["metadata_description"]
    metadata_operation["responses"]["200"]["description"] = text["metadata_response"]
    metadata_operation["responses"]["422"]["description"] = text["validation_error"]
    metadata_operation["responses"]["500"]["description"] = text["server_error"]

    health_operation = schema["paths"]["/api/public/health"]["get"]
    health_operation["summary"] = text["health_summary"]
    health_operation["description"] = text["health_description"]
    health_operation["responses"]["200"]["description"] = text["health_response"]
    health_operation["responses"]["422"]["description"] = text["validation_error"]
    health_operation["responses"]["500"]["description"] = text["server_error"]

    ocr_operation = schema["paths"]["/api/public/ocr-demo"]["post"]
    ocr_operation["summary"] = text["ocr_summary"]
    ocr_operation["description"] = text["ocr_description"]
    ocr_operation["responses"]["200"]["description"] = text["ocr_response"]
    ocr_operation["responses"]["415"]["description"] = text["unsupported_media_type"]
    ocr_operation["responses"]["422"]["description"] = text["validation_error"]
    ocr_operation["responses"]["500"]["description"] = text["server_error"]
    return schema


def build_public_openapi_schema(request: Request, language: str) -> dict:
    cache_key = f"public_openapi_schema_{language.replace('-', '_')}"
    cached_schema = getattr(request.app.state, cache_key, None)
    if cached_schema:
        return cached_schema

    text = PUBLIC_OPENAPI_TEXT[language]
    public_routes = [
        route
        for route in request.app.routes
        if isinstance(route, APIRoute) and route.include_in_schema and route.path in PUBLIC_API_PATHS
    ]
    schema = get_openapi(
        title=text["title"],
        version=settings.app_version,
        description=text["description"],
        routes=public_routes,
        tags=[
            {
                "name": PUBLIC_API_TAG,
                "description": text["tag_description"],
            }
        ],
    )
    apply_public_openapi_language(schema, language)
    setattr(request.app.state, cache_key, schema)
    return schema


@router.get("/docs", include_in_schema=False)
async def public_api_docs(lang: str | None = Query(default=None)):
    language = normalize_public_docs_language(lang)
    text = PUBLIC_OPENAPI_TEXT[language]
    language_json = json.dumps(language)
    label_json = json.dumps(text["language_label"])
    english_json = json.dumps(text["english_label"])
    traditional_chinese_json = json.dumps(text["traditional_chinese_label"])
    title_json = json.dumps(f"{text['title']} - Swagger UI")
    return HTMLResponse(
        f"""
<!DOCTYPE html>
<html>
<head>
  <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
  <title>{text['title']} - Swagger UI</title>
  <style>
    body {{
      margin: 0;
      background: #fafafa;
    }}
    .public-docs-toolbar {{
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      justify-content: flex-end;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid #d9e2ec;
      background: #ffffff;
      font-family: sans-serif;
    }}
    .public-docs-toolbar label {{
      color: #243b53;
      font-size: 0.875rem;
      font-weight: 700;
    }}
    .public-docs-toolbar select {{
      min-width: 150px;
      border: 1px solid #bcccdc;
      border-radius: 6px;
      background: #ffffff;
      color: #102a43;
      font-size: 0.875rem;
      padding: 0.45rem 0.6rem;
    }}
  </style>
</head>
<body>
  <div class="public-docs-toolbar">
    <label for="public-docs-language" id="public-docs-language-label"></label>
    <select id="public-docs-language">
      <option value="zh-TW" id="public-docs-language-zh"></option>
      <option value="en" id="public-docs-language-en"></option>
    </select>
  </div>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    const currentLanguage = {language_json};
    const languageLabel = {label_json};
    const englishLabel = {english_json};
    const traditionalChineseLabel = {traditional_chinese_json};
    const title = {title_json};

    document.title = title;
    document.getElementById('public-docs-language-label').textContent = languageLabel;
    document.getElementById('public-docs-language-en').textContent = englishLabel;
    document.getElementById('public-docs-language-zh').textContent = traditionalChineseLabel;

    const languageSelect = document.getElementById('public-docs-language');
    languageSelect.value = currentLanguage;
    languageSelect.addEventListener('change', (event) => {{
      const nextUrl = new URL(window.location.href);
      nextUrl.searchParams.set('lang', event.target.value);
      window.location.assign(nextUrl.toString());
    }});

    SwaggerUIBundle({{
      url: `/api/public/openapi.json?lang=${{encodeURIComponent(currentLanguage)}}`,
      dom_id: '#swagger-ui',
      deepLinking: true,
      presets: [
        SwaggerUIBundle.presets.apis
      ],
      layout: 'BaseLayout'
    }});
  </script>
</body>
</html>
""",
    )


@router.get("/openapi.json", include_in_schema=False)
async def public_api_openapi(request: Request, lang: str | None = Query(default=None)):
    language = normalize_public_docs_language(lang)
    return build_public_openapi_schema(request, language)


@router.get(
    "",
    response_model=PublicApiInfoResponse,
    summary="Public API metadata",
    description=(
        "Return the public API catalog, documentation URL, authentication policy, "
        "and data handling policy. No authentication is required."
    ),
    response_description="Public API metadata.",
    responses=common_error_responses,
)
async def public_api_info():
    return get_public_api_info()


@router.get(
    "/health",
    response_model=PublicApiHealthResponse,
    summary="Public API health check",
    description=(
        "Return a lightweight health check for the public API router. "
        "This endpoint does not check Supabase, OCR, Ollama, or private business data."
    ),
    response_description="Public API health status.",
    responses=common_error_responses,
)
async def public_api_health():
    return get_public_api_health()


@router.post(
    "/ocr-demo",
    response_model=PublicOcrTextTokensResponse,
    summary="Public OCR demo",
    description=(
        "Upload a JPG, PNG, or PDF file and run OCR only. "
        "The response only includes merged text lines and OCR tokens. "
        "No LLM extraction is performed and no data is persisted. "
        "OCR recognizes one page only; accuracy is not guaranteed for files with more than one page."
    ),
    response_description="OCR texts and tokens.",
    responses={
        **common_error_responses,
        415: {"description": "Only JPG, PNG, and PDF files are supported."},
    },
)
async def public_ocr_demo(
    file: UploadFile = File(..., description="Image or PDF file to recognize. Supports JPG, PNG, and PDF."),
):
    return await run_public_ocr_demo(file)
