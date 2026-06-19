from pydantic import BaseModel, Field


class AppInfoResponse(BaseModel):
    message: str = Field(
        examples=["FastAPI is running"],
        description="API 啟動狀態訊息。",
    )
    app_name: str = Field(
        examples=["智慧發票管理與自動對帳系統 API"],
        description="後端服務名稱。",
    )
    version: str = Field(
        examples=["0.1.0"],
        description="後端服務版本。",
    )
    environment: str = Field(
        examples=["development"],
        description="目前執行環境，例如 development、test 或 production。",
    )


class HealthResponse(BaseModel):
    status: str = Field(
        examples=["ok"],
        description="後端服務健康狀態。",
    )
    service: str = Field(
        examples=["智慧發票管理與自動對帳系統 API"],
        description="被檢查的後端服務名稱。",
    )
    environment: str = Field(
        examples=["development"],
        description="目前執行環境。",
    )


class SupabaseHealthResponse(BaseModel):
    status: str = Field(
        examples=["ok"],
        description="Supabase 連線檢查結果。",
    )
    configured: bool = Field(
        examples=[True],
        description="後端是否已設定 Supabase 連線所需的環境變數。",
    )
    detail: str = Field(
        examples=["Supabase REST API reachable (HTTP 200)"],
        description="Supabase 連線檢查的詳細結果。",
    )


class OllamaGenerateRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        examples=["從「採購人員 王先生」抽出採購人員，只回答值。"],
        description="要送給 Ollama 的提示詞。",
    )
    model: str | None = Field(
        default=None,
        examples=["qwen3.5:0.8b"],
        description="可選的 Ollama 模型名稱；未填時使用後端環境變數 OLLAMA_MODEL。",
    )
    system: str | None = Field(
        default=None,
        examples=["You are a strict JSON extractor."],
        description="可選的系統提示詞，用來指定模型角色或輸出規則。",
    )
    format: str | None = Field(
        default=None,
        examples=["json"],
        description="可選的 Ollama 回應格式，例如 json。",
    )
    think: bool | None = Field(
        default=False,
        description="是否啟用 Ollama thinking 輸出；欄位抽取建議保持 false。",
    )
    temperature: float = Field(
        default=0,
        ge=0,
        le=2,
        description="取樣溫度，越低越穩定。",
    )
    num_predict: int = Field(
        default=4096,
        ge=1,
        le=4096,
        description="最大生成 token 數。",
    )


class OllamaGenerateResponse(BaseModel):
    model: str = Field(examples=["qwen3.5:0.8b"], description="實際使用的 Ollama 模型。")
    response: str = Field(examples=["王先生"], description="Ollama 原始文字回應。")
    thinking: str | None = Field(default=None, description="Ollama 思考內容；think=false 時通常為 null。")
    done: bool = Field(examples=[True], description="Ollama 是否已完成生成。")
    done_reason: str | None = Field(default=None, description="Ollama 停止原因，例如 stop 或 length。")
    total_duration: int | None = Field(default=None, description="Ollama 總耗時，單位為奈秒。")
    load_duration: int | None = Field(default=None, description="模型載入耗時，單位為奈秒。")
    prompt_eval_count: int | None = Field(default=None, description="提示詞評估 token 數。")
    eval_count: int | None = Field(default=None, description="生成 token 數。")


class OllamaPurchaseOrderExtractRequest(BaseModel):
    ocr: dict = Field(
        ...,
        description="原始 OCR 結果，至少需包含 text，可選擇包含 tokens。",
    )
    model: str | None = Field(
        default=None,
        examples=["qwen3.5:0.8b"],
        description="可選的 Ollama 模型名稱；未填時使用後端環境變數 OLLAMA_MODEL。",
    )
    temperature: float = Field(
        default=0,
        ge=0,
        le=2,
        description="取樣溫度，欄位抽取建議使用 0。",
    )
    num_predict: int = Field(
        default=4096,
        ge=1,
        le=4096,
        description="最大生成 token 數。",
    )
    think: bool | None = Field(
        default=False,
        description="是否啟用 Ollama thinking 輸出；JSON 欄位抽取建議保持 false。",
    )


class OllamaPurchaseOrderExtractResponse(OllamaGenerateResponse):
    parsed: dict | None = Field(
        default=None,
        description="當模型回應為合法 JSON 時，後端解析出的 JSON 物件。",
    )


class OllamaGoodsReceiptExtractRequest(OllamaPurchaseOrderExtractRequest):
    pass


class OllamaGoodsReceiptExtractResponse(OllamaPurchaseOrderExtractResponse):
    pass


class OllamaInvoiceExtractRequest(OllamaPurchaseOrderExtractRequest):
    pass


class OllamaInvoiceExtractResponse(OllamaPurchaseOrderExtractResponse):
    pass
