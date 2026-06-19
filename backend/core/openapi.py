api_description = """
## 智慧發票管理與自動對帳系統 API

本 API 提供員工端單據 OCR、採購單建檔、驗收單建檔、發票送出與退回重送流程。

### 認證方式

需要登入的 API 請在 Swagger 右上角 **Authorize** 輸入 Supabase access token：

```text
Bearer <access_token>
```

### 檔案上傳

OCR 與單據送出 API 使用 `multipart/form-data` 上傳檔案，支援 PDF、JPG、PNG。
表單資料欄位如 `poData`、`grData`、`invoiceData` 需傳入 JSON 字串。
"""

openapi_tags = [
    {
        "name": "系統",
        "description": "系統資訊、健康檢查與 Supabase 連線檢查 API。",
    },
    {
        "name": "身分驗證",
        "description": "驗證 Supabase JWT，並取得目前登入使用者資訊。",
    },
    {
        "name": "員工單據",
        "description": "員工端採購單、驗收單、發票 OCR 與送出流程 API。",
    },
    {
        "name": "財務會計",
        "description": "採購單審核、三方媒合、附件預覽與個人操作紀錄 API。",
    },
]

auth_error_responses = {
    401: {"description": "未提供有效的 Authorization Bearer token，或 token 已過期/無效。"},
}

common_error_responses = {
    422: {"description": "請求資料格式錯誤，或必要欄位未填。"},
    500: {"description": "伺服器內部錯誤，通常為外部服務或資料庫操作失敗。"},
}

upload_error_responses = {
    **auth_error_responses,
    415: {"description": "檔案格式不支援；目前僅支援 PDF、JPG、PNG。"},
    **common_error_responses,
}

submit_error_responses = {
    **upload_error_responses,
    400: {"description": "單據資料不符合業務規則，例如採購單號未核准。"},
    409: {"description": "目前單據狀態不允許執行此操作。"},
}
