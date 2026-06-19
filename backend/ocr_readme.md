# 單據 OCR 辨識系統與 DB 寫入 API

以 PaddleOCR + FastAPI 建構的單據辨識 MVP，支援三種單據類型：**請購單**、**採購單**、**發票**、**驗收單**。
流程分為兩階段：先掃描 (OCR 端點)，前端讓使用者確認後，再送出寫入資料庫 (DB 寫入端點)。

---

## 專案結構

├── main.py          # FastAPI 伺服器，含 OCR 與 DB 寫入 Endpoint
├── db.py            # Supabase RPC 呼叫與 Storage 上傳邏輯
├── extractor.py     # 結構化抽取邏輯 (Regex + 空間感知)
├── index.html       # 測試用前端頁面 (包含兩階段送出邏輯)
├── requirements.txt
└── README.md

---

## API Endpoints 分佈

### 階段一：OCR 掃描辨識 (不寫入資料庫)
**Request**：`multipart/form-data`，欄位名稱 `invoiceFile` (支援 JPG/PNG/PDF)

| Method | Path | 說明 |
|--------|------|------|
| `POST` | `/api/employee/requisitions/ocr` | 請購單辨識 |
| `POST` | `/api/employee/purchase-orders/ocr`| 採購單辨識 |
| `POST` | `/api/employee/invoices/ocr` | 發票辨識 |
| `POST` | `/api/employee/goods-receipts/ocr` | 驗收單辨識 |

### 階段二：寫入資料庫 (建立單據)
**Request**：`multipart/form-data` (詳細欄位請參考 `main.py` 參數定義)

| Method | Path | 說明 |
|--------|------|------|
| `POST` | `/api/employee/purchase-orders` | 建立採購單 + 上傳檔案 |
| `POST` | `/api/employee/goods-receipts`  | 建立驗收單 + 上傳檔案 |
| `POST` | `/api/employee/invoices`        | 建立發票 + 上傳檔案 |
| `GET`  | `/api/employee/invoices/rejected` | 查詢被退回的發票 |
| `PUT`  | `/api/employee/invoices/{invoiceNo}` | 修改並重送被退回的發票 |

---

## 重要回傳結構說明 (階段一 OCR)

### 採購單 `/api/employee/purchase-orders/ocr`
```json
{
  "doc_type": "purchase_order",
  "po_number": "B-231",
  "vendor_name": "台電",
  "tax_id": "88888",
  "total_amount": 5000000,
  "items": [
    {
      "line_no": 1,
      "item_name": "三明治",
      "qty": 2,
      "unit_price": 1500000.0,
      "line_amount": 3000000
    }
  ]
}
驗收單 /api/employee/goods-receipts/ocr
⚠️ 前端注意：後端預設將 accepted_qty (合格數量) 設為等於 received_qty (收貨數量)。前端介面請提供表格讓使用者修改不良品的 accepted_qty 後再送出。
{
  "doc_type": "goods_receipt",
  "raw_po_no": "B-231",
  "receipt_date": "2026-04-02",
  "total_qty": 6,
  "total_amount": 5000000,
  "items": [
    {
      "line_no": 1,
      "item_name": "三明治",
      "received_qty": 2,
      "accepted_qty": 2,    // 預設與收貨數量相同，前端送出前可修改
      "line_amount": 3000000
    }
  ]
}
發票 /api/employee/invoices/ocr
⚠️ 前端注意：發票通常不會印採購單號，前端介面必須讓使用者手動輸入/選擇關聯的 poNo，才能打 /api/employee/invoices API 成功寫入。
{
  "invoiceNo": "XX012345678",
  "invoiceDate": "2025-04-20",
  "vendorName": "周小生",
  "totalAmount": 5000000,
  "items": [
    {
      "itemName": "三明治",
      "quantity": 2,
      "unitPrice": 1500000
    }
  ]
}