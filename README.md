# Intelligent Invoice Management and Automated Reconciliation System

智慧發票管理與自動對帳系統。此專案提供一般員工、財務會計、財務主管與系統管理者使用的單據管理流程，支援採購單、驗收單、發票的 OCR 辨識、欄位校正、送審、三方媒合與退回重送。

系統採用前後端分離架構：

- `frontend`: Vue 3 / Vite 前端介面
- `backend`: FastAPI 後端 API、Celery 背景任務、Supabase RPC / Storage 整合
- `ocr-service`: 獨立 FastAPI OCR 服務，使用 PaddleOCR / PyMuPDF
- `ollama`: LLM 欄位抽取服務，將 OCR 結果轉成結構化 JSON
- `redis`: Celery broker / result backend
- `supabase`: 身分驗證、資料庫 RPC、文件儲存

## 系統目標

本系統主要解決紙本或 PDF 單據進入企業流程後的人工輸入與對帳成本：

1. 一般員工上傳採購單、驗收單、發票。
2. OCR 擷取文字與座標 tokens。
3. 程式先根據 tokens 找出表格，轉成 markdown table / JSON table。
4. LLM 根據 OCR 文字、表格與 schema 輸出欄位 JSON。
5. 後端 normalizer 套用規則檢查與欄位修正。
6. 前端顯示可編輯草稿，讓使用者確認後送出。
7. 財務端審核採購單，並執行 PO / GR / Invoice 三方媒合。
8. 財務可核准、暫緩或退回單據；員工可修正退回資料後重送。

## 角色與主要頁面

前端依 Supabase profile 的 `role_code` 導向不同頁面：

| 角色 | role_code | 頁面 | 功能 |
| --- | --- | --- | --- |
| 一般員工 | `E` | `/employee-dashboard` | 上傳 OCR、確認採購單/驗收單/發票、查看送出與退回紀錄 |
| 財務會計 | `A` | `/finance` | 審核採購單、檢視三方媒合、核准/退回/暫緩單據 |
| 財務主管 | `M` | `/finance-manager` | 查看財務審核與媒合彙整資訊 |
| 系統管理者 | `AD` | `/admin` | 使用者與系統管理 |

登入與註冊使用 Supabase Auth：

- `/login`
- `/register`
- `/auth/callback`
- `/auth/pending`

## 核心資料流程

```text
User uploads PDF/image
  |
  v
Frontend Vue form
  |
  | multipart/form-data
  v
FastAPI backend
  |
  | sends file to OCR service
  v
ocr-service
  |
  | PaddleOCR returns text + tokens with coordinates
  v
Backend table extractor
  |
  | detect line-item table from OCR tokens
  | build markdown table + JSON rows
  v
Ollama LLM
  |
  | schema-guided JSON extraction
  v
Backend normalizer
  |
  | fix OCR confusions, dates, amounts, table shifts
  | validate with Pydantic schema
  v
Frontend draft form
  |
  | user confirms fields
  v
Supabase RPC + Storage
```

目前 OCR 不是單純把整段文字丟給 LLM。後端會先利用 OCR token 的座標資訊找出明細表，再把表格轉成 markdown / JSON，讓 LLM 專注在根據 schema 產出結構化欄位。最後再由程式規則做可信度更高的校正。

## OCR 與 LLM 設計

### 採購單 PO

流程：

```text
OCR tokens
  -> 找出採購單明細表
  -> 轉成 markdown table / JSON table
  -> LLM 輸出 PurchaseOrderOcrResponse
  -> normalizer 修正採購單號、日期、金額、明細欄位
```

重點規則：

- 採購單號 `poNo` 會優先從 OCR 幾何與文字規則修正，避免誤抓成請購單號。
- 明細項目會依表格欄位位置解析，降低品名、數量、單價、金額錯位。
- `O/o`、`I/l/|` 會在數字語境中轉成 `0`、`1`。

### 驗收單 GR

流程：

```text
OCR tokens
  -> 找出驗收明細表
  -> 轉成 markdown table / JSON table
  -> LLM 輸出 GoodsReceiptOcrResponse
  -> normalizer 修正驗收單號、數量、金額、明細列
```

重點規則：

- 過濾 OCR 或 LLM 可能誤產生的摘要列，例如把「材料 / 合計」當成明細。
- 若明細金額因欄位錯位不合理，會根據總額與列資料做 reconciliation。
- 驗收單送出時仍會檢查 `poNo` 是否為已核准採購單。

### 發票 Invoice

流程：

```text
OCR tokens
  -> 找出發票明細表
  -> 轉成 markdown table / JSON table
  -> LLM 輸出 InvoiceOcrResponse
  -> normalizer 修正發票號碼、日期、統編、金額、明細
```

重點規則：

- 發票 OCR 階段不抽採購單號，`poNo` 會強制為 `null`。
- 使用者在 Step 2 從已核准採購單中選擇對應 `poNo`。
- 發票號碼支援 `SD012345678` 這類字軌格式，並處理：
  - `O/o` 被誤判成 `0`
  - `I/l/|` 被誤判成 `1`
  - 發票號碼黏在標籤後面，例如 `發票字軌號碼SD012345678`
  - OCR 把字軌與數字拆成多個 token，例如 `SD` + `012345678`

## 專案結構

```text
.
├─ frontend/                 # Vue 3 / Vite frontend
│  ├─ src/
│  │  ├─ views/              # role-based pages
│  │  ├─ router/             # Vue Router and auth guards
│  │  ├─ locales/            # i18n text
│  │  ├─ mocks/              # MSW mock handlers
│  │  ├─ api.js              # frontend API helper
│  │  └─ supabase.js         # Supabase client
│  ├─ e2e/                   # Playwright tests
│  ├─ public/                # static assets and sample documents
│  ├─ Dockerfile
│  └─ Caddyfile
│
├─ backend/                  # FastAPI backend
│  ├─ main.py                # app entrypoint
│  ├─ celery_app.py          # Celery app
│  ├─ routers/               # API routes
│  ├─ schemas/               # Pydantic request/response models
│  ├─ services/              # business logic
│  │  ├─ employee/           # employee flows and OCR normalizers
│  │  ├─ finance/            # finance review and match groups
│  │  ├─ manager/            # finance manager summaries
│  │  ├─ integrations/       # Supabase RPC / Storage wrappers
│  │  ├─ ocr/                # OCR jobs, Celery tasks, OCR client
│  │  └─ system/             # health check and Ollama integration
│  ├─ core/                  # config, auth, logging, OpenAPI helpers
│  ├─ middlewares/           # request logging middleware
│  ├─ tests/                 # pytest contract tests
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ requirements-dev.txt
│
├─ ocr-service/              # standalone OCR API
│  ├─ app/main.py
│  ├─ Dockerfile
│  └─ requirements.txt
│
├─ docs/                     # diagrams and development notes
├─ docker-compose.yml        # base compose
├─ docker-compose.override.yml
└─ docker-compose.prod.yml
```

## Backend 架構

### `routers/`

路由層只負責 HTTP 介面：

- 解析 query、form、file、body
- 套用 auth dependency
- 指定 response model
- 呼叫 service

主要 router：

| 檔案 | Base path | 說明 |
| --- | --- | --- |
| `auth.py` | `/auth` | 取得目前登入使用者 |
| `system.py` | `/`, `/health`, `/llm/ollama/*` | 系統資訊、health check、Ollama 測試 |
| `employee.py` | `/api/employee` | 員工上傳、OCR、送出、重送 |
| `finance.py` | `/api/finance` | 財務審核、媒合、核准、退回、紀錄 |
| `manager.py` | `/api/manager` | 財務主管查詢介面 |
| `public.py` | `/api/public` | 不需登入的公開 metadata、health、OCR demo 與 Public Swagger/OpenAPI |

### `schemas/`

Pydantic models 定義 API contract：

- `employee.py`: PO / GR / Invoice OCR response、送出 payload、退回重送資料
- `finance.py`: 財務待審、媒合群組、審核結果、紀錄
- `auth.py`: 使用者資訊
- `system.py`: health check、Ollama request/response
- `public.py`: Public API metadata、health、OCR texts/tokens response

### `services/employee/`

一般員工流程的核心實作：

- `employee_service.py`: OCR、送出、查詢、重送的 orchestration
- `invoice_ocr_normalizer.py`: 發票表格解析與欄位規則修正
- `procurement_ocr_normalizer.py`: 採購單與驗收單表格解析與欄位規則修正
- `document_mapper.py`: 舊 OCR mapper 與資料轉換輔助

### `services/system/ollama_service.py`

負責：

- 建立 PO / GR / Invoice 專用 prompt
- 將 OCR text、tokens、table context 傳給 Ollama
- 要求 JSON format
- 解析 LLM 回傳 JSON
- 記錄抽取結果與錯誤

### `services/system/public_service.py`

公開 API 的 service layer：

- 組裝 `GET /api/public` metadata 與 data policy。
- 組裝 `GET /api/public/health` 輕量健康檢查。
- 執行 `POST /api/public/ocr-demo`，復用 `services.ocr.ocr_service.run_ocr`，只回傳 `texts` 與 `tokens`。
- 不呼叫 Ollama、不寫入 Supabase、不讀取私有文件。

### `services/integrations/`

外部服務整合集中在這裡：

- `supabase_document_service.py`: Supabase RPC 呼叫
- `document_storage_service.py`: Supabase Storage 檔案上傳與取回

router 與 feature service 不直接散落 Supabase 呼叫，避免資料來源耦合到 API 層。

### `services/ocr/`

負責 OCR 任務與背景處理：

- `ocr_service.py`: 呼叫獨立 OCR service
- `job_service.py`: 建立 async OCR job
- `job_store.py`: Redis job 狀態儲存
- `tasks.py`: Celery 任務
- `document_extractor.py`: 保留部分文字解析工具

## Frontend 架構

前端使用 Vue 3、Vite、Vue Router、Vue I18n、Supabase JS。

主要頁面：

| 檔案 | 說明 |
| --- | --- |
| `views/auth/Login.vue` | 登入 |
| `views/auth/Register.vue` | 註冊 |
| `views/employee/EmployeeDashboard.vue` | 員工單據上傳、OCR 草稿確認、送出、退回重送 |
| `views/finance/MatchGroupWorkbench.vue` | 財務三方媒合工作台 |
| `views/finance_mgr/FinanceManager.vue` | 財務主管頁 |
| `views/admin/Admin.vue` | 系統管理頁 |
| `views/public/PublicApi.vue` | 公開 API 文件入口，會導向獨立 Public Swagger |
| `views/public/PublicOcrDemo.vue` | 公開 OCR 體驗頁，可上傳檔案並依 OCR token 座標預覽辨識結果 |

`router/index.js` 會根據 Supabase session 與 profile role 導向對應頁面。開發時可用 `VITE_DISABLE_ACCESS_MANAGEMENT=true` 放寬角色檢查。

### 公開 API 文件入口

`/public-api` 是不需登入即可使用的公開 API 文件入口。前端會直接導向獨立的 Public API Swagger，不再讀取舊的 Supabase Edge Function 文件。登入頁左側的 `Swagger API 文件` 與 `OCR 體驗` 會以新分頁開啟，不影響目前登入流程：

```env
VITE_SWAGGER_DOCS_URL=
```

未設定 `VITE_SWAGGER_DOCS_URL` 時，development 會導向 `http://localhost:8000/api/public/docs`，production 會導向同網域的 `/api/public/docs`。

Public API Swagger 支援同頁切換語系：

- 預設繁體中文：`http://localhost:8000/api/public/docs`
- 英文模式：`http://localhost:8000/api/public/docs?lang=en`
- OpenAPI JSON 也可指定語系：`/api/public/openapi.json?lang=zh-TW` 或 `/api/public/openapi.json?lang=en`
- 公開 OCR 體驗頁：`http://localhost:5173/public-ocr-demo`

Public API 目前只公開展示用途端點，不需要 Authorization：

- `GET /api/public`: 回傳公開 API metadata、文件 URL、data policy 與 endpoint 清單。
- `GET /api/public/health`: 只檢查 public router 是否可回應，不檢查 Supabase、OCR、Ollama，避免公開 health 洩漏內部依賴狀態。
- `POST /api/public/ocr-demo`: 上傳 PDF / JPG / PNG，只執行 OCR，回傳 `texts` 與 `tokens`。不執行 LLM 欄位抽取、不保存資料。OCR 只辨識一頁，超過一頁不保證準確。

公開 OCR 體驗頁會呼叫 `POST /api/public/ocr-demo`，並把結果分成兩種視圖：

- 左側顯示原始上傳檔案，方便比對。
- 右側根據 `tokens[].x` / `tokens[].y` 重新定位辨識文字，呈現類似 OCR bounding preview 的效果。
- 下方列出 `texts` 合併文字行，方便檢查 API 原始輸出。

## OCR Service 架構

`ocr-service` 是獨立 FastAPI app，提供：

- `GET /health`
- `POST /ocr`

支援格式：

- PDF
- JPEG
- PNG

PDF 會先透過 PyMuPDF render 第一頁，再交給 PaddleOCR。OCR 回傳包含：

- `text`: 合併後文字
- `tokens`: 每個 OCR token 的文字、座標與信心分數
- `metadata`: 檔案與 OCR 執行資訊

後端會使用 tokens 的 `x` / `y` 座標重建表格。

## API 概覽

### Public

- `GET /api/public`
- `GET /api/public/health`
- `POST /api/public/ocr-demo`: 公開 OCR 體驗，只回傳 `texts` 與 `tokens`，不執行 LLM、不保存資料；OCR 只辨識一頁，超過一頁不保證準確

### Auth

- `GET /auth/me`

### System

- `GET /`
- `GET /health`
- `GET /health/supabase`
- `POST /llm/ollama/test`
- `POST /llm/ollama/purchase-order/extract`
- `POST /llm/ollama/goods-receipt/extract`
- `POST /llm/ollama/invoice/extract`

### Employee

Base path: `/api/employee`

- `GET /ocr/status`
- `GET /ocr-jobs/{job_id}`
- `POST /purchase-orders/ocr`
- `POST /purchase-orders`
- `GET /purchase-orders/approved`
- `POST /goods-receipts/ocr`
- `POST /goods-receipts`
- `POST /invoices/ocr`
- `POST /invoices`
- `GET /documents/rejected`
- `PUT /invoices/{invoice_no}`
- `GET /documents`
- `GET /documents/{doc_id}`
- `PUT /documents/{doc_id}`
- `DELETE /documents/{doc_id}`
- `GET /documents/{doc_id}/file`

### Finance

Base path: `/api/finance`

- `GET /purchase-orders/pending`
- `GET /purchase-orders/{po_no}`
- `GET /purchase-orders/{po_no}/file`
- `POST /purchase-orders/{po_no}/review`
- `GET /match-groups/pending`
- `GET /match-groups/review-groups`
- `GET /match-groups/{po_no}`
- `GET /match-groups/{po_no}/po/file`
- `GET /match-groups/{po_no}/gr/file`
- `GET /match-groups/{po_no}/invoice/file`
- `POST /match-groups/{po_no}/auto-review`
- `POST /match-groups/{po_no}/approve`
- `POST /match-groups/{po_no}/reject`
- `POST /match-groups/{po_no}/hold`
- `POST /match-groups/{po_no}/void`
- `GET /logs`
- `GET /documents/history`
- `GET /employee-operation-records`

### Manager

Base path: `/api/manager`

- `GET /claims`
- `GET /claims/{claim_id}`
- `GET /match-groups`
- `GET /match-groups/{po_no}`
- `GET /match-groups/{po_no}/files/{doc_type}`
- `GET /attachments/{storage_path}`

## 環境變數

開發環境通常需要：

```text
backend/.env.dev
frontend/.env.dev
```

可從範例複製：

```powershell
Copy-Item backend\.env.example backend\.env.dev
Copy-Item frontend\.env.example frontend\.env.dev
```

後端常用設定：

```env
APP_ENV=development
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=
ALLOW_DEV_FALLBACK=1
TEST_USER_ID=test-user-id
OCR_SERVICE_URL=http://ocr-service:8001
OCR_REQUEST_TIMEOUT=180
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen3.5:0.8b
OLLAMA_REQUEST_TIMEOUT=300
```

前端常用設定：

```env
VITE_API_BASE=/api
VITE_PROXY_TARGET=http://backend:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
VITE_DISABLE_ACCESS_MANAGEMENT=false
VITE_SWAGGER_DOCS_URL=
```

## Docker Start

建議使用 Docker Compose 啟動完整系統。Compose 會啟動：

- `web`: Vue frontend
- `backend`: FastAPI backend
- `celery-worker`: OCR 背景任務 worker
- `ocr-service`: PaddleOCR service
- `redis`: Celery broker / result backend
- `ollama`: LLM runtime
- `ollama-pull`: 啟動時確認模型存在

目前預設模型是 `qwen3.5:9b`。如果要改模型，必須確認 Ollama 裡已經有該模型，或讓 `ollama-pull` 成功拉下來。

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml exec ollama ollama list
```

如果要使用其他模型：

```powershell
$env:OLLAMA_MODEL="gemma3:270m"
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

或手動拉模型：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml exec ollama ollama pull gemma3:270m
```

### Development 啟動

第一次啟動或 Dockerfile / dependencies 有改：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d --build
```

平常啟動：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

查看服務狀態：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml ps
```

Development 入口：

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Public Swagger: http://localhost:8000/api/public/docs
- Public OCR demo: http://localhost:5173/public-ocr-demo
- Backend health: http://localhost:8000/health
- OCR service: http://localhost:8001
- OCR health: http://localhost:8001/health
- Ollama: http://localhost:11434

### Development hot reload

`docker-compose.override.yml` 會掛載本機程式碼：

- `./frontend:/app`
- `./backend:/app`
- `./ocr-service/app:/app/app`

因此一般程式碼異動不需要 rebuild：

- Frontend: Vite hot reload
- Backend API: uvicorn reload
- Celery worker: `watchmedo` 偵測 `.py` 後自動重啟 worker
- OCR service: uvicorn reload

如果 hot reload 沒吃到變更，先重啟指定服務即可，不需要 rebuild：

```powershell
docker compose restart web
docker compose restart backend
docker compose restart ocr-service
```

如果想明確指定 development compose 檔，也可以使用：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml restart web
```

只有改到以下內容才需要 rebuild：

- `Dockerfile`
- `requirements*.txt`
- `package.json`
- `package-lock.json`
- 系統套件或 image base

指定服務 rebuild：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml build backend
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d backend celery-worker
```

### 常用 Docker 指令

看 logs：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml logs -f
docker compose -f docker-compose.yml -f docker-compose.override.yml logs -f backend
docker compose -f docker-compose.yml -f docker-compose.override.yml logs -f celery-worker
docker compose -f docker-compose.yml -f docker-compose.override.yml logs -f ocr-service
docker compose -f docker-compose.yml -f docker-compose.override.yml logs -f web
docker compose -f docker-compose.yml -f docker-compose.override.yml logs -f ollama
```

進入 backend container：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml exec backend sh
```

查看 Ollama 模型：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml exec ollama ollama list
```

測試 Ollama：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml exec ollama ollama run qwen3.5:0.8b
```

停止服務：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml down
```

重新建立 container：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d --force-recreate
```

### Production 啟動

Production 使用 base compose 加上 production override：

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

平常啟動：

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

停止 production：

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```

Production 入口：

- Web: http://localhost:8080
- API: http://localhost:8080/api
- Health: http://localhost:8080/api/health

Production 的 backend 不直接對外開 `localhost:8000`，而是由 `web` container 內的 Caddy 反向代理 `/api`。

### Dev / Prod 切換注意

如果剛跑過 production，再切回 development，建議明確指定 compose 檔：

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

反過來也是：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml down
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

這可以避免同一個 project name 下殘留 prod container，造成「改了程式但沒有生效」或「pytest 不存在」之類的錯覺。

## 測試

### Backend pytest

在 Docker development container 中執行：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml exec backend pytest
```

指定測試：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml exec backend pytest tests/test_employee_api_contract.py
docker compose -f docker-compose.yml -f docker-compose.override.yml exec backend pytest tests/test_finance_api_contract.py
docker compose -f docker-compose.yml -f docker-compose.override.yml exec backend pytest tests/test_auth_jwt.py
docker compose -f docker-compose.yml -f docker-compose.override.yml exec backend pytest tests/test_public_api_contract.py
```

`tests/test_public_api_contract.py` 會檢查：

- `/api/public` 與 `/api/public/health` 不需登入。
- `/api/public/openapi.json` 只包含 public endpoints，不混入內部 API。
- Public Swagger 支援 `lang=zh-TW` / `lang=en`。
- `/api/public/ocr-demo` 只回傳 `texts` 與 `tokens`。

### Frontend build

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml exec web npm run build
```

### Frontend E2E

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml exec web npm run test:e2e
```

更多測試說明見：

- `docs/testing_guide.md`

## Swagger 使用方式

Development backend 啟動後：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json
- Public Swagger UI: http://localhost:8000/api/public/docs
- Public OpenAPI JSON: http://localhost:8000/api/public/openapi.json

`/docs` 是內部完整 API 文件，包含登入、員工、財務、主管與系統 API。`/api/public/docs` 是公開 API 文件，只會列出不需登入的 public endpoints，並可在同一頁切換繁中 / 英文。

需要登入的 API 可在 Swagger 右上角 `Authorize` 輸入：

```text
Bearer <Supabase access token>
```

若 `backend/.env.dev` 設定：

```env
ALLOW_DEV_FALLBACK=1
TEST_USER_ID=<user-id>
```

沒有帶 Authorization header 時，後端會用 `TEST_USER_ID` 作為開發測試使用者。

## Supabase 整合

此專案依賴 Supabase：

- Supabase Auth: 登入、註冊、JWT
- Supabase Database RPC: 建立單據、審核、媒合、查詢
- Supabase Storage: 上傳與下載 PO / GR / Invoice 附件

後端使用 `SUPABASE_SERVICE_ROLE_KEY` 呼叫 RPC 與 Storage。正式環境請勿開啟 `ALLOW_DEV_FALLBACK`，也不要提交 `.env.dev` / `.env.prod`。

常見 RPC 包含：

- `employee_create_purchase_order`
- `employee_create_goods_receipt`
- `employee_create_invoice`
- `employee_get_approved_purchase_orders`
- `finance_get_pending_purchase_orders`
- `finance_review_purchase_order`
- `finance_get_pending_match_groups`
- `finance_get_match_group_detail`
- `finance_approve_match_group`
- `dev_get_invoice_detail`
- `dev_resubmit_invoice`

實際名稱以 `services/integrations/supabase_document_service.py` 為準。

## 常見問題

### `Ollama request failed: model '...' not found`

代表 backend 指定的 `OLLAMA_MODEL` 不在 Ollama 本機模型列表中。

先查看模型：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml exec ollama ollama list
```

確認 backend 環境變數：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml exec backend python -c "import os; print(os.getenv('OLLAMA_MODEL'))"
```

修法：

- 把 `OLLAMA_MODEL` 改成已存在的模型，例如 `qwen3.5:0.8b`
- 或先 `ollama pull` 需要的模型

### 改後端程式但沒有生效

先確認目前是否跑 dev compose：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml ps
```

應該看到：

- backend image: `iimars-backend:dev`
- celery command: `watchmedo auto-restart`
- web image: `iimars-web:dev`
- ocr-service image: `iimars-ocr-service:dev`

如果看到 `:prod`，請切回 dev：

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

### 改 requirements / package.json 沒生效

這類變更需要 rebuild image：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d --build
```

或只 rebuild 指定服務：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml build backend
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d backend celery-worker
```

### OCR service 很久才 ready

第一次啟動 PaddleOCR 可能要下載或初始化模型。

查看 logs：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml logs -f ocr-service
```

查看 health：

```powershell
Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing
```

### Ollama 沒有使用 GPU

查看 Ollama logs：

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml logs -f ollama
```

確認 Windows / WSL2 / Docker 都看得到 GPU：

```powershell
nvidia-smi
wsl nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

### 發票 OCR 的 `poNo` 是 `null`

這是刻意設計。發票 OCR 階段不從發票推測採購單號，避免誤填其他單據的欄位。使用者需在前端 Step 2 選擇已核准採購單，送出時才會寫入 `invoiceData.poNo`。

相關 API：

```text
GET /api/employee/purchase-orders/approved
POST /api/employee/invoices
```

## 相關文件

- `backend/README.md`
- `frontend/readme.md`
- `ocr-service/README.md`
- `docs/testing_guide.md`
- `docs/git_guide.md`
- `docs/class-diagram.md`
- `docs/sequence-diagram/`
