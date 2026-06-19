# Backend README

本資料夾是「智慧發票管理與自動對帳系統」的後端服務，使用 FastAPI 開發，負責提供 API、驗證 Supabase JWT、串接 Supabase RPC / Storage，以及處理員工上傳文件、OCR、財務審核與三方對帳流程。

## 快速開始

### 使用 Docker Compose

在專案根目錄執行：

```powershell
docker compose up --build
```

開發環境會啟動：

- `backend`: FastAPI，預設 http://localhost:8000
- `ocr-service`: 獨立 OCR 服務，預設 http://localhost:8001
- `web`: 前端 Vite，預設 http://localhost:5173

`docker-compose.override.yml` 會讓後端掛載本機 `./backend:/app`，因此修改 Python 檔案後 uvicorn 會自動 reload。

### 只啟動後端

進入 `backend` 後執行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

建議使用 Python 3.12。後端 `requirements.txt` 不再包含 PaddleOCR / paddlepaddle；OCR 重依賴已拆到根目錄的 `ocr-service`。

## Swagger 與 API 文件

後端啟動後可開啟：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json
- Health check: http://localhost:8000/health
- Supabase health check: http://localhost:8000/health/supabase

Swagger UI 不只是看 API 文件，也可以直接測後端 endpoint。打開 `/docs` 後，點開任一 API，按 `Try it out`，填入參數或上傳檔案，再按 `Execute` 就會真的送 request 到本機後端。

測受保護 API 時有兩種方式：

1. 使用真實登入 token
   - 在 Swagger 右上角按 `Authorize`
   - 輸入 `Bearer <Supabase access token>`
   - 再回到 API 點 `Execute`

   如果已經在前端登入，可以打開瀏覽器 DevTools Console，輸入：

   ```js
   const { supabase } = await import('/src/supabase.js');
   console.log((await supabase.auth.getSession()).data.session.access_token);
   ```

   Console 印出的 access token 可以貼到 Swagger 的 `Authorize` 欄位，格式是：

   ```text
   Bearer <access token>
   ```

2. 使用開發 fallback
   - `.env.dev` 設定 `ALLOW_DEV_FALLBACK=1`
   - 設定 `TEST_USER_ID=<測試使用者 id>`
   - 沒有填 Authorization header 時，後端會用 `TEST_USER_ID` 當目前使用者

員工端 OCR / 上傳類 API 也能在 Swagger 測試，因為 FastAPI 會把 `UploadFile` 和 `Form(...)` 自動顯示成表單。常見欄位：

- `poFile` / `grFile` / `invoiceFile`: 選擇 PDF、JPG 或 PNG
- `poData` / `grData` / `invoiceData`: 填 JSON 字串

例如測 `POST /api/employee/invoices` 時，`invoiceData` 要填類似：

```json
{
  "invoiceNo": "INV-2026-001",
  "invoiceDate": "2026-05-27",
  "totalAmount": 1200,
  "vendorName": "Test Vendor",
  "items": []
}
```

注意：Swagger 的 `Execute` 會真的寫入 Supabase 或觸發審核流程，不只是模擬。測試資料請用測試帳號與測試單號。

Swagger 的路徑由 `core/config.py` 讀取環境變數控制：

- `DOCS_URL`，預設 `/docs`
- `REDOC_URL`，預設 `/redoc`
- `OPENAPI_URL`，預設 `/openapi.json`

當 `APP_ENV=production` 且沒有另外設定上述變數時，文件頁會被關閉。若要在正式環境關閉文件，也可以在 `.env.prod` 設成空值：

```env
DOCS_URL=
REDOC_URL=
OPENAPI_URL=
```

## 後端目錄結構

```text
backend/
├─ main.py
├─ Dockerfile
├─ requirements.txt
├─ requirements-dev.txt
├─ pytest.ini
├─ .env.example
├─ .env.dev
├─ .env.prod
├─ core/
├─ middlewares/
├─ routers/
├─ schemas/
├─ services/
├─ models/
├─ tests/
└─ logs/
```

### `main.py`

FastAPI 入口。這裡只做應用程式組裝：

- 建立 `FastAPI(...)`
- 設定 CORS
- 掛上 request logging middleware
- include 各 router
- 依環境設定決定是否啟動 OCR warmup

新增功能時通常不應該把商業邏輯寫在 `main.py`，只在新增 router 後到這裡註冊。

### `core/`

放全域基礎設施與橫切設定。

- `config.py`: 讀取 `.env` / `.env.dev` / `.env.prod`，集中管理 settings
- `auth.py`: 驗證 Supabase access token，支援 `HS256`、`ES256`、`RS256`
- `supabase_client.py`: 建立 Supabase client
- `openapi.py`: Swagger 描述、tag、共用 error responses
- `logging.py`: logging 設定
- `startup_checks.py`: 啟動時輸出環境檢查

原則：會被多個功能共用、和單一業務流程無關的東西放這裡。

### `middlewares/`

放 FastAPI middleware。

目前主要是 `logging.py`，用來記錄 request / response、慢請求與錯誤。

### `routers/`

放 API 路由層。Router 只負責：

- 宣告 HTTP method / path
- 綁定 request body、form、file、dependency
- 指定 response model
- 呼叫 service

不要在 router 寫 Supabase RPC 細節、檔案上傳細節或複雜商業邏輯。

目前路由：

- `auth.py`: `/auth/me`
- `system.py`: `/`、`/health`、`/health/supabase`
- `employee.py`: `/api/employee/*`
- `finance.py`: `/api/finance/*`

### `schemas/`

放 Pydantic model，包含 request / response schema、資料驗證與格式轉換。

- `auth.py`: 目前登入者回傳格式
- `system.py`: app info / health check 回傳格式
- `employee.py`: 員工端 PO、GR、Invoice、OCR、退回重送相關 schema
- `finance.py`: 財務端審核、對帳、log 相關 schema

原則：

- API 對外輸入輸出格式放 `schemas`
- DB / RPC 回來的欄位需要轉成 API 欄位時，可以在 schema 裡提供 `from_rpc(...)`
- 不要把 Supabase client 或外部服務呼叫放進 schema

### `services/`

放業務邏輯與外部整合。Router 會呼叫這裡。

目前分層：

```text
services/
├─ employee/
├─ finance/
├─ integrations/
├─ ocr/
└─ system/
```

- `employee/employee_service.py`: 員工端文件上傳、OCR、建立 PO/GR/Invoice、重送發票
- `employee/document_mapper.py`: 將 OCR parsing 結果整理成前端需要的欄位
- `finance/finance_service.py`: 財務端審核、對帳群組、下載文件、查 log
- `integrations/supabase_document_service.py`: 封裝 Supabase RPC 呼叫
- `integrations/document_storage_service.py`: 封裝 Supabase Storage 上傳、下載、刪除
- `ocr/ocr_service.py`: OCR engine 或外部 OCR service 呼叫
- `ocr/document_extractor.py`: 從 OCR text/tokens 擷取 PO、GR、Invoice 欄位
- `system/system_service.py`: app info、health check、Supabase health check

原則：

- 業務流程放 feature service，例如 `employee_service.py`、`finance_service.py`
- Supabase RPC / Storage 細節放 `services/integrations`
- OCR 執行與 OCR 文字解析放 `services/ocr`
- 若 service 太大，先依「同一個外部系統」或「同一段業務流程」拆檔

### `models/`

目前保留給 ORM 或資料庫模型使用。此專案目前主要透過 Supabase RPC 與 Pydantic schema，不一定會用到傳統 ORM model。

若未來導入 SQLAlchemy 或 domain model，可放這裡；單純 API request / response 不要放這裡，放 `schemas/`。

### `tests/`

放 pytest 測試。

目前包含：

- `test_auth_jwt.py`: JWT 驗證、dev fallback 行為
- `test_employee_api_contract.py`: 員工端 API contract
- `test_finance_api_contract.py`: 財務端 API contract
- `conftest.py`: 測試共用 fixture / mock

執行：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

或在 Docker 內：

```powershell
docker compose exec backend pytest
```

### `logs/`

後端 log 輸出位置。路徑由 `LOG_FILE_PATH` 控制，預設 `logs/app.log`。

## 新增功能時怎麼拆檔

建議流程：

1. 先決定 API 屬於哪個模組
   - 員工上傳 / OCR / 重送：`routers/employee.py`
   - 財務審核 / 對帳：`routers/finance.py`
   - 登入者資訊 / 權限：`routers/auth.py`
   - 健康檢查 / 系統資訊：`routers/system.py`

2. 在 `schemas/` 建立或擴充 request / response model
   - 對外 API 欄位命名要穩定
   - 需要驗證的欄位用 Pydantic validator
   - RPC 欄位轉換可以做成 `from_rpc(...)`

3. 在 `services/` 寫業務邏輯
   - Router 只呼叫 service
   - Service 處理流程、錯誤與資料整理
   - 外部整合再委派給 `services/integrations`

4. 若需要 Supabase
   - RPC 呼叫放 `services/integrations/supabase_document_service.py`
   - Storage 操作放 `services/integrations/document_storage_service.py`
   - 不要在 router 直接呼叫 Supabase client

5. 補測試
   - API contract 測試放 `tests/test_*_api_contract.py`
   - Auth 行為放 `tests/test_auth_jwt.py`
   - 外部服務盡量 mock，不要讓單元測試依賴真實 Supabase 或 OCR

## 主要 API 分組

### Auth

- `GET /auth/me`: 驗證目前 Supabase access token，回傳 user id、email、role、audience

### System

- `GET /`: 後端基本資訊
- `GET /health`: 後端健康檢查
- `GET /health/supabase`: Supabase 連線檢查

### Employee

Base path: `/api/employee`

- `GET /ocr/status`: OCR 狀態
- `POST /purchase-orders/ocr`: 採購單 OCR
- `POST /purchase-orders`: 上傳並建立採購單
- `GET /purchase-orders/approved`: 查詢已核准採購單
- `POST /goods-receipts/ocr`: 收貨單 OCR
- `POST /goods-receipts`: 上傳並建立收貨單
- `POST /invoices/ocr`: 發票 OCR
- `POST /invoices`: 上傳並建立發票
- `GET /documents/rejected`: 查詢被退回單據 (docType=invoice/purchaseOrder/goodsReceipt)
- `PUT /invoices/{invoiceNo}`: 修改並重送被退回發票

### Finance

Base path: `/api/finance`

- `GET /purchase-orders/pending`: 查詢待審核採購單
- `GET /purchase-orders/{poNo}`: 查詢採購單明細
- `GET /purchase-orders/{poNo}/file`: 下載採購單檔案
- `POST /purchase-orders/{poNo}/review`: 核准或退回採購單
- `GET /match-groups/pending`: 查詢待對帳群組
- `GET /match-groups/{poNo}`: 查詢對帳群組明細
- `GET /match-groups/{poNo}/po/file`: 下載 PO 檔案
- `GET /match-groups/{poNo}/gr/file`: 下載 GR 檔案
- `GET /match-groups/{poNo}/invoice/file`: 下載 Invoice 檔案
- `POST /match-groups/{poNo}/approve`: 核准對帳群組
- `POST /match-groups/{poNo}/reject`: 退回對帳群組中的指定文件
- `POST /match-groups/{poNo}/hold`: 暫停處理對帳群組
- `GET /logs`: 查詢目前財務使用者的操作紀錄

## 環境變數

請以 `.env.example` 為範本建立 `.env.dev` 或 `.env.prod`。

常用設定：

```env
APP_NAME="Intelligent Invoice Management API"
APP_VERSION="0.1.0"
APP_ENV="development"
LOG_LEVEL="INFO"
LOG_FILE_PATH="logs/app.log"
CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"

SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
SUPABASE_JWT_SECRET=

ALLOW_DEV_FALLBACK=0
TEST_USER_ID=test-user-001

OCR_SERVICE_URL=
OCR_REQUEST_TIMEOUT=180
```

載入順序在 `core/config.py`：

1. `backend/.env`
2. `backend/.env.dev`，或由 `ENV_FILE` 指定其他檔案

Docker 開發環境會透過 `docker-compose.override.yml` 載入 `./backend/.env.dev`；正式環境會透過 `docker-compose.prod.yml` 載入 `./backend/.env.prod`。

## Auth 與 Supabase JWT

受保護 API 需要帶：

```text
Authorization: Bearer <Supabase access token>
```

後端在 `core/auth.py` 會依 JWT header 的 `alg` 驗證：

- `HS256`: 使用 `SUPABASE_JWT_SECRET`
- `ES256` / `RS256`: 使用 Supabase JWKS，來源為 `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`

開發時若設定：

```env
ALLOW_DEV_FALLBACK=1
TEST_USER_ID=<some-user-id>
```

沒有帶 Authorization header 時，後端會用 `TEST_USER_ID` 當作目前使用者。這只適合本機測試，正式環境一定要關閉。

在 Swagger 測受保護 API 時，按右上角 `Authorize`，填入：

```text
Bearer <Supabase access token>
```

## OCR 行為

OCR 預設透過獨立 `ocr-service` 執行：

- 後端透過 `OCR_SERVICE_URL` 呼叫獨立的 `ocr-service`
- Docker Compose 預設使用 `http://ocr-service:8001`
- PaddleOCR / PyMuPDF / Pillow / numpy 等 OCR 依賴只安裝在 `ocr-service`
- 後端保留本機 OCR fallback 程式碼，但預設 image 不安裝 OCR extras；若未設定 `OCR_SERVICE_URL`，需要自行安裝 OCR 相關依賴

支援上傳格式：

- `application/pdf`
- `image/jpeg`
- `image/png`

OCR service 回傳的文字與 tokens 會交給 Ollama 轉換成 PO / GR / Invoice 欄位 JSON，再由後端 normalization 與 Pydantic schema 驗證後回傳。

## Supabase 串接

本專案後端主要透過 Supabase RPC 完成資料寫入與查詢。

常見 RPC 封裝位置：

- 員工建立文件：`employee_create_purchase_order`、`employee_create_goods_receipt`、`employee_create_invoice`
- 員工查詢：`employee_get_approved_purchase_orders`
- 財務查詢與審核：`finance_get_pending_purchase_orders`、`finance_review_purchase_order`
- 對帳群組：`finance_get_pending_match_groups`、`finance_get_match_group_detail`、`finance_approve_match_group`
- 開發輔助：`dev_list_rejected_invoices`、`dev_get_invoice_detail`、`dev_resubmit_invoice`

檔案上傳與下載透過 Supabase Storage，封裝在 `services/integrations/document_storage_service.py`。

## 測試

安裝開發依賴：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

執行測試：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

指定測試：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_auth_jwt.py -v
.\.venv\Scripts\python.exe -m pytest tests/test_employee_api_contract.py -v
.\.venv\Scripts\python.exe -m pytest tests/test_finance_api_contract.py -v
```

測試應盡量 mock OCR、Supabase client 與外部網路，不要依賴真實服務。

## 常見操作

### 看後端 log

```powershell
docker compose logs -f backend
```

或查看 `backend/logs/app.log`。

### 進入後端容器

```powershell
docker compose exec backend powershell
```

若容器內沒有 PowerShell，可改用：

```powershell
docker compose exec backend sh
```

### 測 health check

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
Invoke-WebRequest -Uri "http://localhost:8000/health/supabase" -UseBasicParsing
```

### 用 curl / PowerShell 帶 token

```powershell
Invoke-WebRequest `
  -Uri "http://localhost:8000/auth/me" `
  -Headers @{Authorization="Bearer <Supabase access token>"} `
  -UseBasicParsing
```

## 注意事項

- `old_*.py` 是舊版實作或備份，不是目前主要入口；新功能請不要接在舊檔。
- 目前多數 Swagger summary / description 來自 `core/openapi.py` 與 router 內文字；若文件頁出現亂碼，優先檢查檔案編碼是否為 UTF-8。
- 正式環境不要開 `ALLOW_DEV_FALLBACK`。
- 正式環境不要提交真實 `.env.prod` secret。
- Router、schema、service 的分層要維持乾淨，之後功能增加才不會變成單一大檔。
