# 測試指南

## 一、測試架構概覽

本專案在 `test/add-core-tests` 分支新增了三個層次的測試，涵蓋後端純函數、API 路由驗證、以及前端端對端流程。

```
backend/
├── pytest.ini                  # pytest 設定檔
└── tests/
    ├── __init__.py
    ├── conftest.py             # 測試前的 mock 注入（PaddleOCR、Supabase 等）
    ├── test_extractor.py       # Unit Tests（21 個）
    └── test_api.py             # Integration Tests（5 個）

frontend/
├── playwright.config.js        # Playwright 設定檔
└── e2e/
    └── employee-flow.spec.js   # E2E Tests（6 個）
```

---

## 二、各層次測試說明

### 1. Unit Tests（後端，pytest）

**檔案**：`backend/tests/test_extractor.py`

測試 `extractor.py` 中的純函數，無任何外部依賴。

| 類別 | 測試函數 | 說明 |
|------|---------|------|
| `TestParseDate` | `test_minguo_slash` | 民國年 `111/01/15` → `2022-01-15` |
| | `test_minguo_dash` | 民國年 `111-03-20` → `2022-03-20` |
| | `test_western_dash` | 西元年 `2022-01-15` 直接回傳 |
| | `test_western_slash` | 西元年 slash 格式 `2023/06/30` |
| | `test_chinese_era_format` | 中文格式 `112年03月20日` → `2023-03-20` |
| | `test_embedded_in_text` | 日期嵌在文字中也能抓到 |
| | `test_invalid_returns_none` | 無日期 → `None` |
| | `test_empty_returns_none` | 空字串 → `None` |
| `TestParseAmount` | `test_integer_with_comma` | `"1,234"` → `1234` |
| | `test_plain_integer` | `"500"` → `500` |
| | `test_large_amount` | `"1,000,000"` → `1000000` |
| | `test_zero` | `"0"` → `0` |
| | `test_decimal_returns_none` | `"1,234.56"` → `None`（不支援小數） |
| | `test_non_numeric_returns_none` | `"abc"` → `None` |
| | `test_none_input_returns_none` | `None` 輸入 → `None` |
| `TestExtractInvoiceData` | `test_doc_type_is_invoice` | 回傳結果的 `doc_type` 為 `"invoice"` |
| | `test_finds_invoice_number_from_token` | 從 token 找出發票號碼 `AB12345678` |
| | `test_finds_invoice_number_from_merged_text` | 無 token 時從 merged_text 抓 |
| | `test_parses_date_from_merged_text` | 從文字中解析日期 |
| | `test_parses_total_amount` | 從文字中解析合計金額 |
| | `test_empty_input_returns_defaults` | 空輸入時所有欄位為 `None` |

---

### 2. Integration Tests（後端，pytest + httpx）

**檔案**：`backend/tests/test_api.py`

測試 FastAPI 路由的請求驗證行為。PaddleOCR、Supabase、fitz、PIL 皆被 `conftest.py` mock 掉，不需要真實環境。

| 測試函數 | Endpoint | 測試情境 | 預期回應 |
|---------|---------|---------|---------|
| `test_ocr_rejects_plain_text_file` | POST `/api/employee/invoices/ocr` | 上傳 `.txt` 檔案 | `415` |
| `test_po_ocr_rejects_plain_text_file` | POST `/api/employee/purchase-orders/ocr` | 上傳 `.txt` 檔案 | `415` |
| `test_submit_invoice_invalid_json` | POST `/api/employee/invoices` | `invoiceData` 非合法 JSON | `400` |
| `test_submit_invoice_missing_required_fields` | POST `/api/employee/invoices` | 缺少 `invoiceNo`/`invoiceDate`/`totalAmount` | `400` |
| `test_submit_invoice_missing_file` | POST `/api/employee/invoices` | 未附 `invoiceFile` | `422` |

> **為什麼 415、不是 400？**  
> `_check_file()` 驗證檔案型別不合規時拋出 `HTTP 415 Unsupported Media Type`，這是 HTTP 標準語意。

---

### 3. E2E Tests（前端，Playwright）

**檔案**：`frontend/e2e/employee-flow.spec.js`

測試前端登入頁的真實瀏覽器行為。Playwright 攔截所有 `supabase.co` 請求，讓應用程式以「未登入」狀態渲染，不需要真實帳號。

| 測試名稱 | 說明 |
|---------|------|
| `should display the system title on landing page` | 頁面標題 `.system-title` 顯示「發票對帳管理系統」 |
| `should show three section tabs on landing page` | `.dashboard-btn` 共有 3 個（系統概覽、功能示範、公開資訊） |
| `should show Google and email login buttons when not logged in` | `.google-btn` 和 `.email-btn` 可見 |
| `should open email login dialog when clicking email login button` | 點擊後 `.auth-dialog` 出現，email/password 輸入框可見 |
| `should switch UI language to English` | 語系選單切換為 `en`，按鈕文字跟著切換 |
| `should switch to demo section when clicking 功能示範` | 點擊後 `.demo-flow` 出現 |

> **目前限制**：員工的 OCR → 提交完整流程需要模擬 Supabase auth session（進一步的 localStorage injection），留待後續擴充。

---

## 三、如何跑測試

### 前提：確認 Python 環境

後端測試使用全域 Python 3.9，如果你有 venv 請先啟動：

```bash
# 若有 venv（在 backend/ 目錄下）
cd backend
.\.venv\Scripts\activate    # Windows
# source .venv/bin/activate   # Mac/Linux
```

---

### 跑後端 Unit + Integration Tests

```bash
cd backend

# 安裝測試依賴（只需做一次）
pip install -r requirements.txt

# 跑所有後端測試
pytest tests/ -v

# 只跑 unit tests
pytest tests/test_extractor.py -v

# 只跑 integration tests
pytest tests/test_api.py -v
```

預期輸出：

```
26 passed in 1.02s
```

---

### 跑前端 E2E Tests

```bash
cd frontend

# 安裝依賴（只需做一次）
npm install

# 安裝 Playwright 瀏覽器（只需做一次）
npx playwright install chromium

# 跑 E2E 測試（會自動啟動 Vite dev server）
npm run test:e2e
```

或者直接：

```bash
npx playwright test
```

若 Vite dev server 已經在跑（`npm run dev`），Playwright 會直接複用它（`reuseExistingServer: true`），不會重複啟動。

預期輸出：

```
6 passed (11.6s)
```

---

### 一次跑完所有測試

```bash
# 後端
cd backend && pytest tests/ -v

# 前端（另開終端機）
cd frontend && npm run test:e2e
```

---

## 四、測試相關設定檔

| 檔案 | 說明 |
|------|------|
| `backend/pytest.ini` | testpaths、asyncio_mode=auto |
| `backend/tests/conftest.py` | 在 import main.py 前 mock 掉重量級模組 |
| `frontend/playwright.config.js` | Chromium、baseURL、webServer 自動啟動 |

---

## 五、日後新增測試的建議

- **新增業務邏輯函數** → 在 `backend/tests/test_extractor.py` 補對應的 unit test
- **新增 API 路由** → 在 `backend/tests/test_api.py` 補驗證行為的 integration test
- **新增前端頁面** → 在 `frontend/e2e/` 新增 `.spec.js` 檔案

不需要每個函數都補滿，優先測試有複雜邏輯或容易出錯的部分。
