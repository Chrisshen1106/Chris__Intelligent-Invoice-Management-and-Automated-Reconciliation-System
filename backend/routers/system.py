from fastapi import APIRouter

from core.openapi import common_error_responses
from schemas.system import (
    AppInfoResponse,
    HealthResponse,
    OllamaGenerateRequest,
    OllamaGenerateResponse,
    OllamaGoodsReceiptExtractRequest,
    OllamaGoodsReceiptExtractResponse,
    OllamaInvoiceExtractRequest,
    OllamaInvoiceExtractResponse,
    OllamaPurchaseOrderExtractRequest,
    OllamaPurchaseOrderExtractResponse,
    SupabaseHealthResponse,
)
from services.system.ollama_service import (
    extract_goods_receipt_with_ollama,
    extract_invoice_with_ollama,
    extract_purchase_order_with_ollama,
    generate_with_ollama,
)
from services.system.system_service import (
    get_app_info,
    get_health_status,
    get_supabase_health_status,
)

router = APIRouter(tags=["系統"])


@router.get(
    "/",
    response_model=AppInfoResponse,
    summary="取得應用程式資訊",
    description="回傳後端服務的基本資訊，方便快速確認 API 是否正常啟動。",
    response_description="應用程式基本資訊。",
    responses=common_error_responses,
)
async def root():
    return get_app_info()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="檢查後端服務狀態",
    description="回傳後端服務本身的健康狀態，供 Docker healthcheck 或基本存活監控使用。",
    response_description="後端服務健康狀態。",
    responses=common_error_responses,
)
async def health_check():
    return get_health_status()


@router.get(
    "/health/supabase",
    response_model=SupabaseHealthResponse,
    summary="檢查 Supabase 連線狀態",
    description="確認後端 Supabase 環境變數是否已設定，並檢查 Supabase REST API 是否可連線。",
    response_description="Supabase 連線檢查結果。",
    responses=common_error_responses,
)
async def supabase_health_check():
    return get_supabase_health_status()


@router.post(
    "/llm/ollama/test",
    response_model=OllamaGenerateResponse,
    summary="測試 Ollama 文字生成",
    description="將 prompt 傳送到目前設定的 Ollama 服務，回傳模型生成結果。主要供開發與除錯使用。",
    response_description="Ollama 生成結果。",
    responses=common_error_responses,
)
async def test_ollama(request: OllamaGenerateRequest):
    return await generate_with_ollama(request)


@router.post(
    "/llm/ollama/purchase-order/extract",
    response_model=OllamaPurchaseOrderExtractResponse,
    summary="使用 Ollama 抽取採購單欄位",
    description="將原始 OCR JSON 傳送給 Ollama，轉換成採購單 OCR 回應格式。此端點主要供開發測試，正式流程請使用 /api/employee/purchase-orders/ocr。",
    response_description="Ollama 原始回應與可解析時的解析後 JSON。",
    responses=common_error_responses,
)
async def extract_purchase_order_with_llm(request: OllamaPurchaseOrderExtractRequest):
    return await extract_purchase_order_with_ollama(request)


@router.post(
    "/llm/ollama/goods-receipt/extract",
    response_model=OllamaGoodsReceiptExtractResponse,
    summary="使用 Ollama 抽取驗收單欄位",
    description="將原始 OCR JSON 傳送給 Ollama，轉換成驗收單 OCR 回應格式。此端點主要供開發測試，正式流程請使用 /api/employee/goods-receipts/ocr。",
    response_description="Ollama 原始回應與可解析時的解析後 JSON。",
    responses=common_error_responses,
)
async def extract_goods_receipt_with_llm(request: OllamaGoodsReceiptExtractRequest):
    return await extract_goods_receipt_with_ollama(request)


@router.post(
    "/llm/ollama/invoice/extract",
    response_model=OllamaInvoiceExtractResponse,
    summary="使用 Ollama 抽取發票欄位",
    description="將原始 OCR JSON 傳送給 Ollama，轉換成發票 OCR 回應格式。此端點主要供開發測試，正式流程請使用 /api/employee/invoices/ocr；發票 OCR 階段不辨識 poNo。",
    response_description="Ollama 原始回應與可解析時的解析後 JSON。",
    responses=common_error_responses,
)
async def extract_invoice_with_llm(request: OllamaInvoiceExtractRequest):
    return await extract_invoice_with_ollama(request)
