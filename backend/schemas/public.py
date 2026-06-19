from pydantic import BaseModel, Field


class PublicApiEndpointResponse(BaseModel):
    method: str = Field(examples=["GET"], description="HTTP method for the public endpoint.")
    path: str = Field(examples=["/api/public"], description="Public endpoint path.")
    description: str = Field(examples=["Public API metadata."], description="Endpoint description.")
    status: str = Field(examples=["available"], description="Endpoint availability status.")


class PublicApiDataPolicyResponse(BaseModel):
    persistsData: bool = Field(examples=[False], description="Whether this public API persists submitted data.")
    readsPrivateDocuments: bool = Field(
        examples=[False],
        description="Whether this public API reads private business documents.",
    )


class PublicApiInfoResponse(BaseModel):
    name: str = Field(
        examples=[
            "智慧發票管理與自動對帳系統 / Intelligent Invoice Management and Automated Reconciliation System"
        ],
        description="Public API name.",
    )
    version: str = Field(examples=["0.1.0"], description="Public API version.")
    description: str = Field(
        examples=["Public demo API for the invoice management and reconciliation system."],
        description="Public API description.",
    )
    baseUrl: str = Field(examples=["/api/public"], description="Base URL for public API endpoints.")
    docsUrl: str = Field(examples=["/api/public/docs"], description="Public Swagger documentation URL.")
    healthCheckUrl: str = Field(examples=["/api/public/health"], description="Public API health check URL.")
    authentication: str = Field(examples=["none"], description="Authentication requirement.")
    dataPolicy: PublicApiDataPolicyResponse = Field(description="Public API data handling policy.")
    endpoints: list[PublicApiEndpointResponse] = Field(description="Public API endpoint catalog.")


class PublicApiCheckResponse(BaseModel):
    ok: bool = Field(examples=[True], description="Whether the check passed.")
    error: str | None = Field(default=None, examples=[None], description="Failure detail when the check fails.")


class PublicApiHealthResponse(BaseModel):
    success: bool = Field(examples=[True], description="Whether the public API health check succeeded.")
    service: str = Field(examples=["public-api"], description="Service identifier.")
    status: str = Field(examples=["healthy"], description="Public API health status.")
    version: str = Field(examples=["0.1.0"], description="Public API version.")
    environment: str = Field(examples=["development"], description="Current runtime environment.")
    checkedAt: str = Field(
        examples=["2026-06-02T04:00:00+08:00"],
        description="ISO 8601 timestamp when the health check was generated.",
    )
    checks: dict[str, PublicApiCheckResponse] = Field(description="Public health check results.")


class PublicOcrTokenResponse(BaseModel):
    text: str = Field(examples=["Invoice No"], description="Recognized text segment.")
    x: float = Field(examples=[120.0], description="Left X coordinate of the text block.")
    y: float = Field(examples=[80.0], description="Top Y coordinate of the text block.")
    score: float | None = Field(default=None, examples=[0.98], description="OCR confidence score.")


class PublicOcrTextTokensResponse(BaseModel):
    texts: list[str] = Field(
        examples=[["Invoice No AB12345678", "Total 1000"]],
        description="OCR text lines merged by visual order.",
    )
    tokens: list[PublicOcrTokenResponse] = Field(
        default_factory=list,
        description="OCR text tokens with coordinates and confidence scores.",
    )
