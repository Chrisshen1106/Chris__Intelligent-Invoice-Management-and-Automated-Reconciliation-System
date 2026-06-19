import logging
import os

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
import io
import uuid
import json
import urllib.error
import urllib.request
import uvicorn
import numpy as np
import fitz
from PIL import Image
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from paddleocr import PaddleOCR
from extractor import extract_requisition_data, extract_po_data, extract_invoice_data, extract_receipt_data, extract_with_tokens
from db import (
    upload_to_storage,
    remove_from_storage,
    create_purchase_order as db_create_po,
    create_goods_receipt as db_create_gr,
    create_invoice_with_ocr as db_create_invoice,
    list_rejected_invoices as db_list_rejected,
    resubmit_invoice as db_resubmit_invoice,
    get_invoice_detail_by_no as db_get_invoice_detail,
)
from auth import get_current_user, auth_startup_banner

# 0. Supabase 初始化
supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,   
)

# 1. PaddleOCR 初始化 
print("正在載入 PaddleOCR 模型 (ch)...")
ocr_engine = PaddleOCR(
    use_angle_cls=True,
    lang='ch',
    show_log=False,
    use_gpu=False,
    enable_mkldnn=False,
    ir_optim=False,
)
print("PaddleOCR 模型載入完成！")

def _cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "*")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["*"]


# 2. FastAPI 初始化 
app = FastAPI(title="Invoice OCR MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

auth_startup_banner()

ALLOWED_TYPES = ["image/jpeg", "image/png", "application/pdf"]

# 3. 工具函式 

def _pdf_to_image_numpy(pdf_bytes: bytes) -> np.ndarray:
    """PDF 第一頁轉 numpy array，300 DPI 確保小字辨識率。"""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        return np.array(img)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF 解析失敗: {str(e)}")


def _bytes_to_numpy(image_bytes: bytes) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))


def _get_box_top(line) -> float:
    """取得 OCR 辨識框的頂部 y 座標，相容新舊兩種輸出格式。"""
    if isinstance(line, dict):
        bbox = line.get("rec_bbox") or line.get("bbox")
        if bbox:
            return float(bbox[1])          # [x0, y0, x1, y1]
        box = line.get("box") or line.get("points")
        if box:
            return float(box[0][1])        # [[x0,y0],[x1,y1],[x2,y2],[x3,y3]]
    else:
        return float(line[0][0][1])        # 舊格式 (box, (text, score))
    return 0.0


def _get_box_left(line) -> float:
    """取得 OCR 辨識框的左側 x 座標。"""
    if isinstance(line, dict):
        bbox = line.get("rec_bbox") or line.get("bbox")
        if bbox:
            return float(bbox[0])
        box = line.get("box") or line.get("points")
        if box:
            return float(box[0][0])
    else:
        return float(line[0][0][0])
    return 0.0


def _run_ocr(file_bytes: bytes, content_type: str) -> tuple[str, list[dict]]:
    """
    執行 OCR，回傳 (merged_text, tokens)。

    merged_text：將同一視覺行（y 座標差距 < ROW_TOLERANCE px）的 cell 合併為一行，
                 cell 之間以空格連接，方便 regex 比對「欄位名稱 值」的模式。

    tokens：每個辨識到的文字片段，含 text / x / y / score，
            供 extractor 做 key-next-value 位置感知抓取。

    設計動機：PaddleOCR 對表格型文件會把每個 cell 拆成獨立輸出，
    且 cell 順序不保證由左至右。合併後的 merged_text 讓欄位抓取更穩定。
    """
    img_array = _pdf_to_image_numpy(file_bytes) if content_type == "application/pdf" \
                else _bytes_to_numpy(file_bytes)

    result = ocr_engine.ocr(img_array)
    raw_items = []   # [{text, x, y, score}]

    if result and result[0] is not None:
        for line in result[0]:
            if isinstance(line, dict):
                text  = line.get("rec_text", "") or line.get("text", "")
                score = line.get("rec_score", 1.0)
            else:
                text  = line[1][0]
                score = line[1][1]
            if not text:
                continue
            raw_items.append({
                "text":  text,
                "x":     _get_box_left(line),
                "y":     _get_box_top(line),
                "score": score,
            })

    # 按 y 排序後，把同一視覺行的 cell 合併 
    raw_items.sort(key=lambda t: t["y"])

    ROW_TOLERANCE = 18   # px：y 差距在此範圍內視為同一行
    rows: list[list[dict]] = []
    for item in raw_items:
        if rows and abs(item["y"] - rows[-1][0]["y"]) <= ROW_TOLERANCE:
            rows[-1].append(item)
        else:
            rows.append([item])

    merged_lines = []
    for row in rows:
        row.sort(key=lambda t: t["x"])              # 同行按 x 由左至右
        merged_lines.append(" ".join(t["text"] for t in row))

    merged_text = "\n".join(merged_lines)

    # Debug log 
    print("=== OCR 原始輸出（含信心度）===")
    for t in raw_items:
        mark = " [?]" if t["score"] < 0.7 else ""
        print(f"  [{t['score']:.2f}]{mark} (x={t['x']:.0f}, y={t['y']:.0f}) {t['text']}")
    print("--- 合併後各行 ---")
    for line in merged_lines:
        print(f"  {line}")

    return merged_text, raw_items


def _check_file(file: UploadFile):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="僅支援 JPG、PNG 或 PDF")


# 4. 路由

@app.get("/")
async def read_index():
    return {"status": "ok", "service": "Invoice OCR MVP"}


# 4-1. 請購單 
@app.post("/api/employee/requisitions/ocr")
async def requisition_ocr(
    invoiceFile: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
):
    """
    請購單掃描 → 結構化欄位
    回傳欄位：申請人、請購日期、請購編號、請購部門、公司名稱、廠商編號、合計、明細
    """
    _check_file(invoiceFile)
    merged_text, tokens = _run_ocr(await invoiceFile.read(), invoiceFile.content_type)
    s = extract_requisition_data(merged_text, tokens)
    print(f"[requisition] structured: {s}")

    return {
        "doc_type":         s["doc_type"],
        "applicant":        s.get("applicant"),        # 申請人
        "requisition_date": s.get("requisition_date"), # 請購日期
        "requisition_no":   s.get("requisition_no"),   # 請購編號
        "department":       s.get("department"),        # 請購部門
        "company_name":     s.get("company_name"),      # 公司名稱
        "vendor_no":        s.get("vendor_no"),         # 廠商編號
        "total_amount":     s.get("total_amount"),
        "items":            s.get("items", []),
        # items 各行包含：item_no, material_no, name, quantity, unit_price, amount
    }


# 4-2. 採購單
@app.post("/api/employee/purchase-orders/ocr")
async def purchase_order_ocr(
    invoiceFile: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
):
    """
    採購單掃描 → 結構化欄位 (對齊 DB core.purchase_orders & purchase_order_items)
    """
    _check_file(invoiceFile)
    merged_text, tokens = _run_ocr(await invoiceFile.read(), invoiceFile.content_type)
    s = extract_po_data(merged_text, tokens)
    print(f"[purchase_order] structured: {s}")

    # 對齊採購單「明細」(Items) 的欄位
    aligned_items = []
    for item in s.get("items", []):
        try:
            line_no = int(item.get("item_no")) if item.get("item_no") else None
        except (ValueError, TypeError):
            line_no = None

        # 嘗試推算 unit_price (如果有總價跟數量的話)
        qty = item.get("quantity")
        line_amount = item.get("subtotal")
        unit_price = None
        if qty and line_amount and qty > 0:
            unit_price = round(line_amount / qty, 2)

        aligned_items.append({
            "line_no":     line_no,              # DB 對齊
            "item_name":   item.get("name"),     # DB 對齊
            "spec":        item.get("spec"),     # DB 對齊
            "qty":         qty,                  # DB 對齊
            "unit":        item.get("unit"),     # DB 無此欄，保留供前端顯示
            "unit_price":  unit_price,           # DB 對齊 (由 subtotal / qty 推算)
            "line_amount": line_amount,          # DB 對齊 (extractor 回傳 subtotal)
        })

    return {
        "doc_type":       s["doc_type"],
        "purchaser":      s.get("purchaser"),       # 保留我的
        "department":     s.get("department"),      # 保留我的
        "requisition_no": s.get("requisition_no"),  # 保留我的
        "po_number":      s.get("po_number"),       # 保留我的
        "order_date":     s.get("order_date"),      # 採購日期 (DB 的 purchase_orders.order_date 必填)
        "vendor_name":    s.get("vendor_name"),     # 保留我的
        "tax_id":         s.get("tax_id"),          # 保留我的 (後續要拿來找 vendor_id)
        "total_amount":   s.get("total_amount"),    # 保留我的
        "items":          aligned_items             # 套用對齊後的明細
    }


# 4-3. 發票 OCR
@app.post("/api/employee/invoices/ocr")
async def invoice_ocr(
    invoiceFile: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
):
    """
    發票掃描 → 結構化欄位 (對齊 DB core.invoices)
    """
    _check_file(invoiceFile)
    merged_text, tokens = _run_ocr(await invoiceFile.read(), invoiceFile.content_type)
    s = extract_invoice_data(merged_text, tokens)
    print(f"[invoice] structured: {s}")
 
    # 明細轉 camelCase，對齊 SDM_API.md 2.3：{ itemName, quantity, unitPrice }
    aligned_items = [
        {
            "itemName":  item.get("name"),
            "quantity":  item.get("quantity"),
            "unitPrice": item.get("unit_price"),
        }
        for item in s.get("items", [])
    ]
 
    # 回傳欄位對齊 SDM_API.md 2.3，使用 camelCase
    # DB 內部欄位由後端自行處理，不暴露給前端
    return {
        "invoiceNo":   s.get("invoice_number"),
        "poNo":        s.get("po_number"),
        "invoiceDate": s.get("date"),
        "vendorName":  s.get("vendor_name"),
        "totalAmount": s.get("total_amount"),
        "items":       aligned_items,
    }

#4.4. 驗收單 OCR
@app.post("/api/employee/goods-receipts/ocr")
async def goods_receipt_ocr(
    invoiceFile: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
):
    """
    驗收單掃描 → 結構化欄位 (對齊 DB core.goods_receipts & items)
    """
    _check_file(invoiceFile)
    merged_text, tokens = _run_ocr(await invoiceFile.read(), invoiceFile.content_type)
    s = extract_receipt_data(merged_text, tokens)
    print(f"[goods_receipt] structured: {s}")

    # 對齊驗收單「明細」(Items) 的欄位
    aligned_items = []
    for item in s.get("items", []):
        try:
            line_no = int(item.get("item_no")) if item.get("item_no") else None
        except (ValueError, TypeError):
            line_no = None

        received_qty = item.get("quantity")

        aligned_items.append({
            "line_no": line_no,                      
            "item_name": item.get("name"),           
            "purchase_order_item_id": None,          
            "received_qty": received_qty,            
            # DB 的驗收合格數量 (單項)：因為紙本單據只有「總合格量」，這裡預設帶入收貨數量，前端可再調整
            "accepted_qty": received_qty,           
            "line_amount": item.get("amount")        # 接上 OCR 抓到的「明細金額」
        })

    return {
        "doc_type":     s["doc_type"],
        "gr_no":        s.get("gr_no"),         # 驗收單號 (DB 的 goods_receipts.gr_no 是 unique 必填)
        "raw_po_no":    s.get("po_number"),     
        "applicant":    s.get("applicant"),     
        "receiver":     s.get("receiver"),      
        "receipt_date": s.get("receipt_date"),  
        "total_qty":    s.get("total_qty"),     
        "total_amount": s.get("total_amount"),  
        "items":        aligned_items           
    }

# 4-5. 通用測試端點（給 index.html 用）
@app.post("/api/ocr")
async def do_ocr(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
):
    _check_file(file)
    merged_text, _ = _run_ocr(await file.read(), file.content_type)
    return {"filename": file.filename, "raw_text": merged_text}


# 4-6. 送出（三種單據共用同一支送出 API）
@app.post("/api/employee/documents")
async def submit_document(
    invoiceFile: UploadFile = File(...),
    invoiceData: str = Form(...),    # 前端傳來的 JSON 字串，含 docType
    current_user: str = Depends(get_current_user),
):
    """
    統一送出端點，前端在 invoiceData 裡帶入 docType 區分單據類型。
    docType: "requisition" | "purchase_order" | "invoice"
    """
    try:
        doc_dict = json.loads(invoiceData)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invoiceData 不是合法的 JSON 字串")

    doc_type = doc_dict.get("docType", "unknown")
    print(f"[submit] docType={doc_type}, file={invoiceFile.filename}")
    print(f"[submit] data={doc_dict}")

    # TODO: 依 doc_type 分別串接資料庫儲存邏輯
    doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"

    return {
        "docId":   doc_id,
        "docType": doc_type,
        "status":  "pending_review",
        "message": "單據已成功送出"
    }


# 5. 員工送出 / 查詢路由  (對齊 SDM_API.md 第 2 章)
# 5-1. 建立／上傳採購單 (SDM_API.md 2.1)
@app.post("/api/employee/purchase-orders")
async def create_purchase_order(
    poNo:        str           = Form(...),   # 採購單號
    poDate:      str           = Form(...),   # 採購日期 (YYYY-MM-DD)
    vendorName:  str           = Form(...),   # 供應商名稱
    totalAmount: int           = Form(...),   # 採購總金額
    taxId:       str           = Form(None),  # 統編 (從 OCR 結果帶過來)
    items:       str           = Form(...),   # 明細 (JSON 字串)
    poFile:      UploadFile    = File(...),   # 採購單檔案 (pdf/png/jpg)
    current_user: str          = Depends(get_current_user),
):
    if poFile.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="僅支援 JPG、PNG 或 PDF")

    # 解析 items JSON
    try:
        items_list = json.loads(items)
        if not isinstance(items_list, list):
            raise ValueError("items 必須是 array")
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"items 不是合法的 JSON array: {e}")

    # 讀檔
    file_bytes = await poFile.read()

    # 1) 上傳 Storage
    try:
        file_meta = upload_to_storage(
            entity_type="purchase_order",
            entity_no=poNo,
            filename=poFile.filename,
            file_bytes=file_bytes,
            content_type=poFile.content_type,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"檔案上傳失敗: {e}")

    file_meta["uploaded_by"] = current_user

    # 2) 呼叫 RPC 建 PO + items + 附件 metadata (一個 transaction)
    try:
        po = db_create_po(
            vendor_tax_id=taxId,
            vendor_name=vendorName,
            po_no=poNo,
            order_date=poDate,
            total_amount=totalAmount,
            requester_user_id=current_user,
            items=items_list,
            files=[file_meta],
        )
    except Exception as e:
        # 補償刪除 Storage 上的檔案
        remove_from_storage(file_meta["bucket_id"], file_meta["storage_path"])
        raise HTTPException(status_code=500, detail=f"建立採購單失敗: {e}")

    return {
        "success": True,
        "poId":    po.get("id"),
        "poNo":    po.get("po_no"),
        "message": "採購單已成功建立",
    }


# 5-2. 建立／上傳驗收單
@app.post("/api/employee/goods-receipts")
async def create_goods_receipt(
    grNo:   str        = Form(...),   # 驗收單號
    poNo:   str        = Form(...),   # 關聯的採購單號
    grDate: str        = Form(...),   # 驗收日期 (YYYY-MM-DD)
    items:  str        = Form(...),   # 明細 (JSON 字串)
    grFile: UploadFile = File(...),   # 驗收單檔案 (pdf/png/jpg)
    current_user: str  = Depends(get_current_user),
):
    if grFile.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="僅支援 JPG、PNG 或 PDF")

    try:
        items_list = json.loads(items)
        if not isinstance(items_list, list):
            raise ValueError("items 必須是 array")
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"items 不是合法的 JSON array: {e}")

    file_bytes = await grFile.read()

    try:
        file_meta = upload_to_storage(
            entity_type="goods_receipt",
            entity_no=grNo,
            filename=grFile.filename,
            file_bytes=file_bytes,
            content_type=grFile.content_type,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"檔案上傳失敗: {e}")

    file_meta["uploaded_by"] = current_user

    try:
        gr = db_create_gr(
            po_no=poNo,
            gr_no=grNo,
            received_date=grDate,
            received_by=current_user,
            items=items_list,
            files=[file_meta],
        )
    except Exception as e:
        remove_from_storage(file_meta["bucket_id"], file_meta["storage_path"])
        raise HTTPException(status_code=500, detail=f"建立驗收單失敗: {e}")

    return {
        "success": True,
        "grId":    gr.get("id"),
        "grNo":    gr.get("gr_no"),
        "message": "驗收單已成功建立",
    }


# 5-3. 確認並送出發票 Step 2 
@app.post("/api/employee/invoices")
async def submit_invoice(
    invoiceFile: UploadFile = File(...),   # 發票檔案
    invoiceData: str        = Form(...),   # 前端確認/修改後的 JSON 字串化資料
    current_user: str       = Depends(get_current_user),
):
    if invoiceFile.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="僅支援 JPG、PNG 或 PDF")

    try:
        data_dict = json.loads(invoiceData)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invoiceData 不是合法的 JSON 字串")

    # 取必填欄位 (前端 OCR 確認後送過來的)
    invoice_no   = data_dict.get("invoiceNo")
    invoice_date = data_dict.get("invoiceDate")
    total_amount = data_dict.get("totalAmount")
    if not (invoice_no and invoice_date and total_amount is not None):
        raise HTTPException(status_code=400, detail="invoiceNo / invoiceDate / totalAmount 不能空")

    file_bytes = await invoiceFile.read()
    try:
        file_meta = upload_to_storage(
            entity_type="invoice",
            entity_no=invoice_no,
            filename=invoiceFile.filename,
            file_bytes=file_bytes,
            content_type=invoiceFile.content_type,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"檔案上傳失敗: {e}")
    file_meta["uploaded_by"] = current_user

    # 把 items 包進 ocr_parsed_json (DB 沒有 invoice_items 表,明細放 ocr_runs)
    ocr_parsed = {"items": data_dict.get("items", [])}

    try:
        invoice = db_create_invoice(
            employee_id=current_user,
            invoice_no=invoice_no,
            invoice_date=invoice_date,
            total_amount=total_amount,
            vendor_name=data_dict.get("vendorName"),
            po_no=data_dict.get("poNo"),
            tax_rate=data_dict.get("taxRate"),
            ocr_parsed_json=ocr_parsed,
            ocr_provider="paddleocr",
            files=[file_meta],
        )
    except Exception as e:
        remove_from_storage(file_meta["bucket_id"], file_meta["storage_path"])
        raise HTTPException(status_code=500, detail=f"建立發票失敗: {e}")

    return {
        "invoiceId": invoice.get("id"),
        "invoiceNo": invoice.get("invoice_no"),
        "status":    invoice.get("workflow_status"),
        "message":   "發票已成功送出",
    }


# 5-4. 取得被退回的發票清單 
@app.get("/api/employee/invoices/rejected")
async def get_rejected_invoices(
    current_user: str = Depends(get_current_user),
):
    try:
        return db_list_rejected(employee_id=current_user, limit=50)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢失敗: {e}")


# 5-5. 重新編輯並送出退回發票
@app.put("/api/employee/invoices/{invoiceNo}")
async def resubmit_invoice(
    invoiceNo:   str,                              # Path 參數:發票號碼
    invoiceFile: UploadFile | None = File(None),   # 新的發票檔案 (若有重新上傳才帶)
    invoiceData: str               = Form(...),    # 修正後的 JSON 字串化資料
    current_user: str              = Depends(get_current_user),
):
    if invoiceFile and invoiceFile.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="僅支援 JPG、PNG 或 PDF")

    try:
        data_dict = json.loads(invoiceData)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invoiceData 不是合法的 JSON 字串")

    # 先撈發票拿 id (dev_resubmit_invoice 要 invoice_id 不是 invoice_no)
    try:
        detail = db_get_invoice_detail(invoiceNo)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"找不到發票 {invoiceNo}: {e}")
    invoice_id = detail.get("id") if isinstance(detail, dict) else None
    if not invoice_id:
        raise HTTPException(status_code=404, detail=f"找不到發票 {invoiceNo}")

    field_changes = data_dict.get("changes", [])

    try:
        result = db_resubmit_invoice(
            invoice_id=invoice_id,
            acted_by=current_user,
            field_changes=field_changes,
            comment=data_dict.get("comment"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重送發票失敗: {e}")

    return {
        "success":   True,
        "invoiceNo": result.get("invoice_no"),
        "status":    result.get("workflow_status"),
        "message":   "發票已重新送出審核",
    }

#======================= 財務主管報表
def _manager_claim_status(row: dict) -> tuple[int, str]:
    status_code = row.get("statusCode") or row.get("status_code")
    status_text = row.get("status") or row.get("statusDescription") or row.get("status_description")

    if isinstance(status_code, int):
        code = status_code
    elif isinstance(status_code, str) and status_code.isdigit():
        code = int(status_code)
    elif status_text in {"approved", "已同意"}:
        code = 2
    elif status_text in {"rejected", "已拒絕"}:
        code = 3
    else:
        code = 1

    descriptions = {
        1: "待核准",
        2: "已同意",
        3: "已拒絕",
    }
    return code, descriptions.get(code, str(status_text or "待核准"))


def _normalize_manager_claim(row: dict, idx: int) -> dict:
    status_code, status_description = _manager_claim_status(row)
    attachment_url = (
        row.get("attachmentUrl")
        or row.get("attachment_url")
        or row.get("attachmentPath")
        or row.get("attachment_path")
    )

    return {
        "claimId": row.get("claimId") or row.get("claim_id") or row.get("invoiceNo") or row.get("invoice_no") or f"CLM-{idx + 1}",
        "applicantName": row.get("applicantName") or row.get("applicant_name") or row.get("employeeName") or row.get("employee_name") or "",
        "expenseItem": row.get("expenseItem") or row.get("expense_item") or row.get("vendorName") or row.get("vendor_name") or row.get("invoiceNo") or "",
        "applyDate": row.get("applyDate") or row.get("apply_date") or row.get("createdAt") or row.get("created_at") or "",
        "amount": row.get("amount") or row.get("totalAmount") or row.get("total_amount") or 0,
        "statusCode": status_code,
        "statusDescription": status_description,
        "attachmentUrl": attachment_url,
    }


def _rpc_as_current_user(function_name: str, payload: dict | None, request: Request):
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="缺少 Authorization header")

    req = urllib.request.Request(
        f"{SUPABASE_URL.rstrip('/')}/rest/v1/rpc/{function_name}",
        data=json.dumps(payload or {}).encode("utf-8"),
        headers={
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as res:
            body = res.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            detail = json.loads(body)
        except json.JSONDecodeError:
            detail = body
        raise HTTPException(status_code=e.code, detail=detail)
    except urllib.error.URLError as e:
        raise HTTPException(status_code=500, detail=f"Supabase RPC 連線失敗: {e}")

    if not body:
        return None
    return json.loads(body)


@app.get("/api/manager/claims")
async def get_manager_claims(
    request: Request,
    current_user: str = Depends(get_current_user),
):
    try:
        rows = _rpc_as_current_user("manager_get_claims", {}, request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢主管審核紀錄失敗: {e}")

    rows = rows or []
    if isinstance(rows, dict):
        rows = rows.get("data") or rows.get("items") or [rows]

    return [
        _normalize_manager_claim(row, idx)
        for idx, row in enumerate(rows)
        if isinstance(row, dict)
    ]


@app.get("/api/manager/invoice")
async def dev_get_invoices(
    limit: int = 50,
    current_user: str = Depends(get_current_user),
):
    response = supabase.rpc(
        "dev_get_invoices",   
        {
            "p_limit": limit,  
        },
    ).execute()

    return response.data 


#=======================
# 6. 啟動
if __name__ == "__main__":
    print("正在啟動 FastAPI 伺服器...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
