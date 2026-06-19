import json

import pytest
from httpx import ASGITransport, AsyncClient

from core.auth import get_current_access_token, get_current_user
from main import app
from services.employee import employee_service
from services.employee.invoice_ocr_normalizer import normalize_invoice_ocr_response
from services.integrations import supabase_document_service


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: "test-user"
    app.dependency_overrides[get_current_access_token] = lambda: "test-access-token"
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def calls():
    return {}


@pytest.fixture(autouse=True)
def mock_common_io(monkeypatch, calls):
    monkeypatch.setattr(employee_service, "run_ocr", lambda file_bytes, content_type: ("raw text", []))

    def fake_upload_to_storage(**kwargs):
        calls.setdefault("uploads", []).append(kwargs)
        return {
            "bucket_id": "documents",
            "storage_path": f"{kwargs['entity_type']}/{kwargs['entity_no']}/{kwargs['filename']}",
            "original_filename": kwargs["filename"],
            "file_type": "pdf",
            "file_size": len(kwargs["file_bytes"]),
        }

    monkeypatch.setattr(employee_service.document_storage_service, "upload_to_storage", fake_upload_to_storage)
    monkeypatch.setattr(employee_service.document_storage_service, "remove_from_storage", lambda *args: None)
    monkeypatch.setattr(
        employee_service.supabase_document_service,
        "list_approved_purchase_orders",
        lambda access_token=None: [{"poNo": "PO-001", "vendorName": "Vendor", "poDate": "2026-05-01"}],
    )


def po_payload():
    return {
        "poNo": "PO-001",
        "purchaser": "Alice",
        "department": "IT",
        "vendorName": "Vendor",
        "taxId": "12345678",
        "poDate": "2026-05-01",
        "totalAmount": 1000,
        "items": [
            {
                "lineNo": 1,
                "itemName": "Laptop",
                "spec": "14 inch",
                "quantity": 2,
                "unitPrice": 500,
                "lineAmount": 1000,
            }
        ],
    }


def gr_payload():
    return {
        "grNo": "GR-001",
        "poNo": "PO-001",
        "applicant": "Alice",
        "receiver": "Bob",
        "grDate": "2026-05-03",
        "totalQty": 2,
        "totalAmount": 1000,
        "items": [
            {
                "lineNo": 1,
                "itemName": "Laptop",
                "receivedQty": 2,
                "acceptedQty": 2,
                "lineAmount": 1000,
            }
        ],
    }


def invoice_payload():
    return {
        "invoiceNo": "INV-001",
        "poNo": "PO-001",
        "invoiceDate": "2026-05-04",
        "vendorName": "Vendor",
        "totalAmount": 1000,
        "taxId": "12345678",
        "items": [{"lineNo": 1, "itemName": "Laptop", "quantity": 2, "unitPrice": 500}],
    }


class FakeRpcResult:
    data = {"id": "created-id"}

    def execute(self):
        return self


class FakeSupabaseClient:
    def __init__(self, calls):
        self.calls = calls

    def rpc(self, function_name, payload):
        self.calls.append((function_name, payload))
        return FakeRpcResult()


@pytest.mark.asyncio
async def test_2_1_purchase_order_ocr_returns_prefill_schema(client, monkeypatch):
    async def fake_extract_purchase_order_with_ollama(request):
        return {
            "model": "test-model",
            "response": "{}",
            "done": True,
            "done_reason": "stop",
            "parsed": {
                "poNo": "PO-001",
                "purchaser": "Alice",
                "department": "IT",
                "vendorName": "Vendor",
                "taxId": "12345678",
                "poDate": "2026-05-01",
                "totalAmount": 1000,
                "items": [
                    {
                        "lineNo": 1,
                        "itemName": "Laptop",
                        "spec": "14 inch",
                        "quantity": 2,
                        "unitPrice": 500,
                        "lineAmount": 1000,
                    }
                ],
            },
        }

    monkeypatch.setattr(
        employee_service,
        "extract_purchase_order_with_ollama",
        fake_extract_purchase_order_with_ollama,
    )

    async with client as c:
        response = await c.post(
            "/api/employee/purchase-orders/ocr",
            files={"poFile": ("po.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json() == po_payload()


@pytest.mark.asyncio
async def test_purchase_order_ocr_uses_table_context_and_corrects_items(client, monkeypatch):
    ocr_text = "\n".join([
        "採購人員 周大帥 採購部門 資訊部",
        "請購單號 PO-TEST-1 採購單號 PO-TEST-123",
        "採購日期 2026-05-28",
        "供應商名稱 聯發科 統一編號 12345678",
        "項次 品名 單價 數量 規格 小計",
        "001 晶片 1000 10 一般規格 10000",
        "002 電池 300 50 pv5 15000",
        "採購合計 25000",
    ])
    ocr_tokens = [
        {"text": "採購人員", "x": 161.0, "y": 249.0, "score": 0.99},
        {"text": "周大帥", "x": 424.0, "y": 248.0, "score": 0.99},
        {"text": "採購部門", "x": 661.0, "y": 250.0, "score": 0.99},
        {"text": "資訊部", "x": 800.0, "y": 246.0, "score": 0.99},
        {"text": "請購單號", "x": 161.0, "y": 301.0, "score": 0.99},
        {"text": "PO-TEST-1", "x": 424.0, "y": 301.0, "score": 0.99},
        {"text": "採購單號", "x": 660.0, "y": 302.0, "score": 0.99},
        {"text": "PO-TEST-123", "x": 803.0, "y": 304.0, "score": 0.99},
        {"text": "採購日期", "x": 161.0, "y": 352.0, "score": 0.99},
        {"text": "2026-05-28", "x": 425.0, "y": 353.0, "score": 0.99},
        {"text": "供應商名稱", "x": 159.0, "y": 400.0, "score": 0.99},
        {"text": "聯發科", "x": 424.0, "y": 402.0, "score": 0.99},
        {"text": "統一編號", "x": 657.0, "y": 402.0, "score": 0.99},
        {"text": "12345678", "x": 802.0, "y": 403.0, "score": 0.99},
        {"text": "項次", "x": 159.0, "y": 682.0, "score": 0.99},
        {"text": "品名", "x": 337.0, "y": 682.0, "score": 0.99},
        {"text": "單價", "x": 422.0, "y": 683.0, "score": 0.99},
        {"text": "數量", "x": 655.0, "y": 679.0, "score": 0.99},
        {"text": "規格", "x": 801.0, "y": 682.0, "score": 0.99},
        {"text": "小計", "x": 960.0, "y": 682.0, "score": 0.99},
        {"text": "001", "x": 158.0, "y": 734.0, "score": 0.99},
        {"text": "晶片", "x": 320.0, "y": 734.0, "score": 0.99},
        {"text": "1000", "x": 424.0, "y": 735.0, "score": 0.99},
        {"text": "10", "x": 655.0, "y": 732.0, "score": 0.99},
        {"text": "一般規格", "x": 803.0, "y": 735.0, "score": 0.99},
        {"text": "10000", "x": 961.0, "y": 737.0, "score": 0.99},
        {"text": "002", "x": 159.0, "y": 785.0, "score": 0.99},
        {"text": "電池", "x": 318.0, "y": 783.0, "score": 0.99},
        {"text": "300", "x": 422.0, "y": 785.0, "score": 0.99},
        {"text": "50", "x": 657.0, "y": 783.0, "score": 0.99},
        {"text": "pv5", "x": 798.0, "y": 786.0, "score": 0.99},
        {"text": "15000", "x": 961.0, "y": 788.0, "score": 0.99},
        {"text": "採購合計", "x": 843.0, "y": 838.0, "score": 0.99},
        {"text": "25000", "x": 958.0, "y": 836.0, "score": 0.99},
    ]
    monkeypatch.setattr(employee_service, "run_ocr", lambda file_bytes, content_type: (ocr_text, ocr_tokens))

    async def fake_extract_purchase_order_with_ollama(request):
        assert request.ocr["tables"][0]["name"] == "purchase_order_line_items"
        assert request.ocr["tables"][0]["rows"][0]["unitPrice"] == 1000.0
        assert request.ocr["tables"][0]["rows"][0]["quantity"] == 10.0
        return {
            "model": "test-model",
            "response": "{}",
            "done": True,
            "done_reason": "stop",
            "parsed": {
                "poNo": "PO-WRONG",
                "purchaser": None,
                "department": None,
                "vendorName": None,
                "taxId": None,
                "poDate": None,
                "totalAmount": 0,
                "items": [
                    {"lineNo": 1, "itemName": "晶片", "spec": None, "quantity": 1000, "unitPrice": 10, "lineAmount": 10000}
                ],
            },
        }

    monkeypatch.setattr(employee_service, "extract_purchase_order_with_ollama", fake_extract_purchase_order_with_ollama)

    async with client as c:
        response = await c.post(
            "/api/employee/purchase-orders/ocr",
            files={"poFile": ("po.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json() == {
        "poNo": "PO-TEST-123",
        "purchaser": "周大帥",
        "department": "資訊部",
        "vendorName": "聯發科",
        "taxId": "12345678",
        "poDate": "2026-05-28",
        "totalAmount": 25000,
        "items": [
            {"lineNo": 1, "itemName": "晶片", "spec": "一般規格", "quantity": 10, "unitPrice": 1000, "lineAmount": 10000},
            {"lineNo": 2, "itemName": "電池", "spec": "pv5", "quantity": 50, "unitPrice": 300, "lineAmount": 15000},
        ],
    }


@pytest.mark.asyncio
async def test_purchase_order_ocr_async_returns_job_id(client, monkeypatch, calls):
    def fake_enqueue_ocr_job(**kwargs):
        calls["enqueue_ocr_job"] = kwargs
        return {
            "jobId": "job-001",
            "status": "queued",
            "documentType": kwargs["document_type"],
            "statusUrl": "/api/employee/ocr-jobs/job-001",
        }

    monkeypatch.setattr(employee_service.job_service, "enqueue_ocr_job", fake_enqueue_ocr_job)

    async with client as c:
        response = await c.post(
            "/api/employee/purchase-orders/ocr?async=true",
            files={"poFile": ("po.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 202
    assert response.json() == {
        "jobId": "job-001",
        "status": "queued",
        "documentType": "purchaseOrder",
        "statusUrl": "/api/employee/ocr-jobs/job-001",
    }
    assert calls["enqueue_ocr_job"]["file_bytes"] == b"%PDF"
    assert calls["enqueue_ocr_job"]["owner_id"] == "test-user"


@pytest.mark.asyncio
async def test_get_ocr_job_returns_completed_result_for_owner(client, monkeypatch):
    monkeypatch.setattr(
        employee_service.job_store,
        "get_job",
        lambda job_id: {
            "jobId": job_id,
            "status": "completed",
            "documentType": "purchaseOrder",
            "filename": "po.pdf",
            "ownerId": "test-user",
            "createdAt": "2026-05-29T00:00:00+00:00",
            "updatedAt": "2026-05-29T00:00:01+00:00",
            "result": po_payload(),
        },
    )

    async with client as c:
        response = await c.get("/api/employee/ocr-jobs/job-001")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["result"] == po_payload()


@pytest.mark.asyncio
async def test_2_2_purchase_order_submit_accepts_file_and_po_data(client, monkeypatch, calls):
    def fake_create_purchase_order(**kwargs):
        calls["create_purchase_order"] = kwargs
        return {"id": "po-id", "po_no": kwargs["po_no"]}

    monkeypatch.setattr(employee_service.supabase_document_service, "create_purchase_order", fake_create_purchase_order)

    async with client as c:
        response = await c.post(
            "/api/employee/purchase-orders",
            data={"poData": json.dumps(po_payload())},
            files={"poFile": ("po.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 201
    assert response.json() == {
        "success": True,
        "poId": "po-id",
        "poNo": "PO-001",
        "message": "Purchase order created successfully",
    }
    assert calls["uploads"][0]["entity_type"] == "purchase_order"
    assert calls["uploads"][0]["entity_no"] == "PO-001"
    assert calls["create_purchase_order"]["vendor_tax_id"] == "12345678"
    assert calls["create_purchase_order"]["access_token"] == "test-access-token"
    assert "requester_user_id" not in calls["create_purchase_order"]
    assert calls["create_purchase_order"]["items"] == [
        {
            "line_no": 1,
            "item_name": "Laptop",
            "spec": "14 inch",
            "qty": 2.0,
            "unit_price": 500.0,
            "line_amount": 1000.0,
        }
    ]


@pytest.mark.asyncio
async def test_2_3_goods_receipt_ocr_returns_prefill_schema(client, monkeypatch):
    async def fake_extract_goods_receipt_with_ollama(request):
        return {
            "model": "test-model",
            "response": "{}",
            "done": True,
            "done_reason": "stop",
            "parsed": gr_payload(),
        }

    monkeypatch.setattr(
        employee_service,
        "extract_goods_receipt_with_ollama",
        fake_extract_goods_receipt_with_ollama,
    )

    async with client as c:
        response = await c.post(
            "/api/employee/goods-receipts/ocr",
            files={"grFile": ("gr.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json() == gr_payload()


@pytest.mark.asyncio
async def test_goods_receipt_ocr_uses_table_context_and_corrects_items(client, monkeypatch):
    ocr_text = "\n".join([
        "驗收單號 GR-TEST-531 採購申請人 周大生",
        "採購人員 周大帥 到貨日期 2026-05-27",
        "驗收人 林小姐 資產種類 材料",
        "項次 品名 收貨數量 金額",
        "001 晶片 10 10000",
        "002 電池 50 300",
        "驗收數量 60",
        "合格數量 60",
        "合計 25000",
    ])
    ocr_tokens = [
        {"text": "驗收單號", "x": 161.0, "y": 326.0, "score": 0.99},
        {"text": "GR-TEST-531", "x": 402.0, "y": 329.0, "score": 0.99},
        {"text": "採購申請人", "x": 638.0, "y": 329.0, "score": 0.99},
        {"text": "周大生", "x": 877.0, "y": 328.0, "score": 0.99},
        {"text": "採購人員", "x": 161.0, "y": 384.0, "score": 0.99},
        {"text": "周大帥", "x": 398.0, "y": 384.0, "score": 0.99},
        {"text": "到貨日期", "x": 640.0, "y": 387.0, "score": 0.99},
        {"text": "2026-05-27", "x": 877.0, "y": 388.0, "score": 0.99},
        {"text": "驗收人", "x": 159.0, "y": 443.0, "score": 0.99},
        {"text": "林小姐", "x": 398.0, "y": 443.0, "score": 0.99},
        {"text": "項次", "x": 159.0, "y": 502.0, "score": 0.99},
        {"text": "品名", "x": 400.0, "y": 501.0, "score": 0.99},
        {"text": "收貨數量", "x": 640.0, "y": 503.0, "score": 0.99},
        {"text": "金額", "x": 877.0, "y": 501.0, "score": 0.99},
        {"text": "001", "x": 159.0, "y": 560.0, "score": 0.99},
        {"text": "晶片", "x": 398.0, "y": 560.0, "score": 0.99},
        {"text": "10", "x": 637.0, "y": 561.0, "score": 0.99},
        {"text": "10000", "x": 876.0, "y": 561.0, "score": 0.99},
        {"text": "002", "x": 159.0, "y": 619.0, "score": 0.99},
        {"text": "電池", "x": 400.0, "y": 619.0, "score": 0.99},
        {"text": "50", "x": 637.0, "y": 619.0, "score": 0.99},
        {"text": "300", "x": 874.0, "y": 620.0, "score": 0.99},
        {"text": "驗收數量", "x": 495.0, "y": 679.0, "score": 0.99},
        {"text": "60", "x": 849.0, "y": 681.0, "score": 0.99},
        {"text": "合格數量", "x": 496.0, "y": 737.0, "score": 0.99},
        {"text": "60", "x": 847.0, "y": 735.0, "score": 0.99},
        {"text": "合計", "x": 795.0, "y": 793.0, "score": 0.99},
        {"text": "25000", "x": 874.0, "y": 796.0, "score": 0.99},
    ]
    monkeypatch.setattr(employee_service, "run_ocr", lambda file_bytes, content_type: (ocr_text, ocr_tokens))

    async def fake_extract_goods_receipt_with_ollama(request):
        assert request.ocr["tables"][0]["name"] == "goods_receipt_line_items"
        assert request.ocr["tables"][0]["rows"][0]["receivedQty"] == 10.0
        assert request.ocr["tables"][0]["rows"][0]["lineAmount"] == 10000.0
        return {
            "model": "test-model",
            "response": "{}",
            "done": True,
            "done_reason": "stop",
            "parsed": {
                "grNo": "GR-WRONG",
                "poNo": None,
                "applicant": None,
                "receiver": None,
                "grDate": None,
                "totalQty": 0,
                "totalAmount": 0,
                "items": [
                    {"lineNo": 1, "itemName": "晶片", "receivedQty": 10000, "acceptedQty": 10000, "lineAmount": 10},
                    {"lineNo": 2, "itemName": "材料", "receivedQty": 60, "acceptedQty": 60, "lineAmount": 25000},
                ],
            },
        }

    monkeypatch.setattr(employee_service, "extract_goods_receipt_with_ollama", fake_extract_goods_receipt_with_ollama)

    async with client as c:
        response = await c.post(
            "/api/employee/goods-receipts/ocr",
            files={"grFile": ("gr.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json() == {
        "grNo": "GR-TEST-531",
        "poNo": None,
        "applicant": "周大生",
        "receiver": "林小姐",
        "grDate": "2026-05-27",
        "totalQty": 60,
        "totalAmount": 25000,
        "items": [
            {"lineNo": 1, "itemName": "晶片", "receivedQty": 10, "acceptedQty": 10, "lineAmount": 10000},
            {"lineNo": 2, "itemName": "電池", "receivedQty": 50, "acceptedQty": 50, "lineAmount": 15000},
        ],
    }


@pytest.mark.asyncio
async def test_2_4_goods_receipt_submit_accepts_file_gr_data_and_approved_po(client, monkeypatch, calls):
    def fake_create_goods_receipt(**kwargs):
        calls["create_goods_receipt"] = kwargs
        return {"id": "gr-id", "gr_no": kwargs["gr_no"]}

    monkeypatch.setattr(employee_service.supabase_document_service, "create_goods_receipt", fake_create_goods_receipt)

    async with client as c:
        response = await c.post(
            "/api/employee/goods-receipts",
            data={"grData": json.dumps(gr_payload())},
            files={"grFile": ("gr.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 201
    assert response.json() == {
        "success": True,
        "grId": "gr-id",
        "grNo": "GR-001",
        "message": "Goods receipt created successfully",
    }
    assert calls["uploads"][0]["entity_type"] == "goods_receipt"
    assert calls["create_goods_receipt"]["po_no"] == "PO-001"
    assert calls["create_goods_receipt"]["access_token"] == "test-access-token"
    assert "received_by" not in calls["create_goods_receipt"]
    assert calls["create_goods_receipt"]["items"] == [
        {
            "line_no": 1,
            "item_name": "Laptop",
            "received_qty": 2.0,
            "accepted_qty": 2.0,
            "line_amount": 1000.0,
        }
    ]


@pytest.mark.asyncio
async def test_2_5_approved_purchase_orders_returns_dropdown_options(client):
    async with client as c:
        response = await c.get("/api/employee/purchase-orders/approved")

    assert response.status_code == 200
    assert response.json() == [{"poNo": "PO-001", "vendorName": "Vendor", "poDate": "2026-05-01"}]


@pytest.mark.asyncio
async def test_2_6_invoice_ocr_returns_prefill_schema(client, monkeypatch):
    async def fake_extract_invoice_with_ollama(request):
        return {
            "model": "test-model",
            "response": "{}",
            "done": True,
            "done_reason": "stop",
            "parsed": {
                "invoiceNo": "INV-001",
                "poNo": "PO-001",
                "invoiceDate": "2026-05-04",
                "vendorName": "Vendor",
                "taxId": "12345678",
                "totalAmount": 1000,
                "items": [{"lineNo": 1, "itemName": "Laptop", "quantity": 2, "unitPrice": 500}],
            },
        }

    monkeypatch.setattr(
        employee_service,
        "extract_invoice_with_ollama",
        fake_extract_invoice_with_ollama,
    )

    async with client as c:
        response = await c.post(
            "/api/employee/invoices/ocr",
            files={"invoiceFile": ("inv.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json() == {
        "invoiceNo": "INV-001",
        "poNo": None,
        "invoiceDate": "2026-05-04",
        "vendorName": "Vendor",
        "taxId": "12345678",
        "totalAmount": 1000,
        "items": [{"lineNo": 1, "itemName": "Laptop", "quantity": 2, "unitPrice": 500}],
    }


@pytest.mark.asyncio
async def test_invoice_ocr_corrects_table_columns_and_roc_date(client, monkeypatch):
    ocr_text = "\n".join([
        "SD012345678",
        "統一編號：12345678 中華民國115年5月28日",
        "品名 數量 單價 金額 備註",
        "晶片 10 1000 10000",
        "電池 50 300 15000 營業人蓋用統一發票專用章",
        "銷售額合計 25000 賣 方： 人生有限公司",
        "統 一編号： 08000800",
        "營業稅 0",
        "總計 25000",
    ])
    ocr_tokens = [
        {"text": "SD012345678", "x": 155.0, "y": 159.0, "score": 0.99},
        {"text": "統一編號：12345678", "x": 152.0, "y": 295.0, "score": 0.96},
        {"text": "中華民國115年5月28日", "x": 536.0, "y": 297.0, "score": 0.99},
        {"text": "品名", "x": 158.0, "y": 423.0, "score": 0.99},
        {"text": "數量", "x": 382.0, "y": 423.0, "score": 0.99},
        {"text": "單價", "x": 478.0, "y": 423.0, "score": 0.99},
        {"text": "金額", "x": 638.0, "y": 421.0, "score": 0.99},
        {"text": "晶片", "x": 159.0, "y": 481.0, "score": 0.99},
        {"text": "10", "x": 382.0, "y": 482.0, "score": 0.99},
        {"text": "1000", "x": 481.0, "y": 484.0, "score": 0.99},
        {"text": "10000", "x": 643.0, "y": 487.0, "score": 0.99},
        {"text": "電池", "x": 159.0, "y": 540.0, "score": 0.99},
        {"text": "50", "x": 381.0, "y": 540.0, "score": 0.99},
        {"text": "300", "x": 478.0, "y": 540.0, "score": 0.99},
        {"text": "15000", "x": 641.0, "y": 541.0, "score": 0.99},
        {"text": "銷售額合計", "x": 161.0, "y": 600.0, "score": 0.99},
        {"text": "25000", "x": 539.0, "y": 600.0, "score": 0.99},
        {"text": "賣", "x": 805.0, "y": 602.0, "score": 0.99},
        {"text": "方：", "x": 873.0, "y": 603.0, "score": 0.99},
        {"text": "人生有限公司", "x": 936.0, "y": 602.0, "score": 0.99},
        {"text": "統", "x": 805.0, "y": 630.0, "score": 0.99},
        {"text": "一編号：", "x": 826.0, "y": 629.0, "score": 0.70},
        {"text": "08000800", "x": 940.0, "y": 631.0, "score": 0.99},
        {"text": "總計", "x": 158.0, "y": 716.0, "score": 0.99},
        {"text": "25000", "x": 540.0, "y": 719.0, "score": 0.99},
    ]
    monkeypatch.setattr(employee_service, "run_ocr", lambda file_bytes, content_type: (ocr_text, ocr_tokens))

    async def fake_extract_invoice_with_ollama(request):
        assert request.ocr["tables"][0]["name"] == "invoice_line_items"
        assert request.ocr["tables"][0]["rows"] == [
            {
                "lineNo": 1,
                "itemName": "晶片",
                "quantity": 10.0,
                "unitPrice": 1000.0,
                "lineAmount": 10000.0,
                "rawText": "晶片 10 1000 10000",
            },
            {
                "lineNo": 2,
                "itemName": "電池",
                "quantity": 50.0,
                "unitPrice": 300.0,
                "lineAmount": 15000.0,
                "rawText": "電池 50 300 15000",
            },
        ]
        assert "| lineNo | itemName | quantity | unitPrice | lineAmount | rawText |" in request.ocr["tables"][0]["markdown"]
        return {
            "model": "test-model",
            "response": "{}",
            "done": True,
            "done_reason": "stop",
            "parsed": {
                "invoiceNo": "SD012345678",
                "poNo": "PO-SHOULD-BE-IGNORED",
                "invoiceDate": "2023-05-28",
                "vendorName": "人生有限公司",
                "taxId": "08000800",
                "totalAmount": 25000,
                "items": [
                    {"lineNo": 1, "itemName": "晶片", "quantity": 10, "unitPrice": 10000},
                    {"lineNo": 2, "itemName": "電池", "quantity": 50, "unitPrice": 15000},
                ],
            },
        }

    monkeypatch.setattr(
        employee_service,
        "extract_invoice_with_ollama",
        fake_extract_invoice_with_ollama,
    )

    async with client as c:
        response = await c.post(
            "/api/employee/invoices/ocr",
            files={"invoiceFile": ("inv.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json() == {
        "invoiceNo": "SD012345678",
        "poNo": None,
        "invoiceDate": "2026-05-28",
        "vendorName": "人生有限公司",
        "taxId": "08000800",
        "totalAmount": 25000,
        "items": [
            {"lineNo": 1, "itemName": "晶片", "quantity": 10, "unitPrice": 1000},
            {"lineNo": 2, "itemName": "電池", "quantity": 50, "unitPrice": 300},
        ],
    }


@pytest.mark.asyncio
async def test_invoice_ocr_normalizes_common_digit_confusions(client, monkeypatch):
    ocr_text = "\n".join([
        "SDO12345678",
        "統一編號：12345678 中華民國115年5月28日",
        "品名 數量 單價 金額 備註",
        "晶片 l0 l000 l0000",
        "電池 5O 3OO l5OOO",
        "銷售額合計 25OOO 賣 方： 人生有限公司",
        "統 一編号： O8OOO8OO",
        "總計 25OOO",
    ])
    ocr_tokens = [
        {"text": "SDO12345678", "x": 155.0, "y": 159.0, "score": 0.99},
        {"text": "中華民國115年5月28日", "x": 536.0, "y": 297.0, "score": 0.99},
        {"text": "品名", "x": 158.0, "y": 423.0, "score": 0.99},
        {"text": "數量", "x": 382.0, "y": 423.0, "score": 0.99},
        {"text": "單價", "x": 478.0, "y": 423.0, "score": 0.99},
        {"text": "金額", "x": 638.0, "y": 421.0, "score": 0.99},
        {"text": "晶片", "x": 159.0, "y": 481.0, "score": 0.99},
        {"text": "l0", "x": 382.0, "y": 482.0, "score": 0.99},
        {"text": "l000", "x": 481.0, "y": 484.0, "score": 0.99},
        {"text": "l0000", "x": 643.0, "y": 487.0, "score": 0.99},
        {"text": "電池", "x": 159.0, "y": 540.0, "score": 0.99},
        {"text": "5O", "x": 381.0, "y": 540.0, "score": 0.99},
        {"text": "3OO", "x": 478.0, "y": 540.0, "score": 0.99},
        {"text": "l5OOO", "x": 641.0, "y": 541.0, "score": 0.99},
        {"text": "銷售額合計", "x": 161.0, "y": 600.0, "score": 0.99},
        {"text": "25OOO", "x": 539.0, "y": 600.0, "score": 0.99},
        {"text": "賣", "x": 805.0, "y": 602.0, "score": 0.99},
        {"text": "方：", "x": 873.0, "y": 603.0, "score": 0.99},
        {"text": "人生有限公司", "x": 936.0, "y": 602.0, "score": 0.99},
        {"text": "統", "x": 805.0, "y": 630.0, "score": 0.99},
        {"text": "一編号：", "x": 826.0, "y": 629.0, "score": 0.70},
        {"text": "O8OOO8OO", "x": 940.0, "y": 631.0, "score": 0.99},
        {"text": "總計", "x": 158.0, "y": 716.0, "score": 0.99},
        {"text": "25OOO", "x": 540.0, "y": 719.0, "score": 0.99},
    ]
    monkeypatch.setattr(employee_service, "run_ocr", lambda file_bytes, content_type: (ocr_text, ocr_tokens))

    async def fake_extract_invoice_with_ollama(request):
        assert request.ocr["tables"][0]["rows"] == [
            {
                "lineNo": 1,
                "itemName": "晶片",
                "quantity": 10.0,
                "unitPrice": 1000.0,
                "lineAmount": 10000.0,
                "rawText": "晶片 l0 l000 l0000",
            },
            {
                "lineNo": 2,
                "itemName": "電池",
                "quantity": 50.0,
                "unitPrice": 300.0,
                "lineAmount": 15000.0,
                "rawText": "電池 5O 3OO l5OOO",
            },
        ]
        return {
            "model": "test-model",
            "response": "{}",
            "done": True,
            "done_reason": "stop",
            "parsed": {
                "invoiceNo": "SDO12345678",
                "poNo": "PO-SHOULD-BE-IGNORED",
                "invoiceDate": "2026-05-28",
                "vendorName": "人生有限公司",
                "taxId": "O8OOO8OO",
                "totalAmount": 25000,
                "items": [],
            },
        }

    monkeypatch.setattr(
        employee_service,
        "extract_invoice_with_ollama",
        fake_extract_invoice_with_ollama,
    )

    async with client as c:
        response = await c.post(
            "/api/employee/invoices/ocr",
            files={"invoiceFile": ("inv.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json() == {
        "invoiceNo": "SD012345678",
        "poNo": None,
        "invoiceDate": "2026-05-28",
        "vendorName": "人生有限公司",
        "taxId": "08000800",
        "totalAmount": 25000,
        "items": [
            {"lineNo": 1, "itemName": "晶片", "quantity": 10, "unitPrice": 1000},
            {"lineNo": 2, "itemName": "電池", "quantity": 50, "unitPrice": 300},
        ],
    }


def test_invoice_ocr_recovers_invoice_no_from_labeled_or_split_tokens():
    labeled = normalize_invoice_ocr_response(
        {"invoiceNo": None, "poNo": None, "items": []},
        "發票字軌號碼SD012345678",
        [{"text": "發票字軌號碼SD012345678", "x": 120.0, "y": 100.0}],
    )
    split = normalize_invoice_ocr_response(
        {"invoiceNo": None, "poNo": None, "items": []},
        "發票字軌號碼 SD 012345678",
        [
            {"text": "發票字軌號碼", "x": 120.0, "y": 100.0},
            {"text": "SD", "x": 240.0, "y": 100.0},
            {"text": "012345678", "x": 280.0, "y": 100.0},
        ],
    )

    assert labeled["invoiceNo"] == "SD012345678"
    assert split["invoiceNo"] == "SD012345678"


@pytest.mark.asyncio
async def test_2_7_invoice_submit_accepts_file_invoice_data_and_approved_po(client, monkeypatch, calls):
    def fake_create_invoice(**kwargs):
        calls["create_invoice"] = kwargs
        return {"id": "invoice-id", "invoice_no": kwargs["invoice_no"], "status": "pendingMatch"}

    monkeypatch.setattr(employee_service.supabase_document_service, "create_invoice", fake_create_invoice)

    async with client as c:
        response = await c.post(
            "/api/employee/invoices",
            data={"invoiceData": json.dumps(invoice_payload())},
            files={"invoiceFile": ("inv.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 201
    assert response.json() == {
        "invoiceId": "invoice-id",
        "invoiceNo": "INV-001",
        "status": "pendingMatch",
        "message": "Invoice submitted successfully",
    }
    assert calls["uploads"][0]["entity_type"] == "invoice"
    assert calls["uploads"][0]["entity_no"] == "INV-001"
    assert calls["create_invoice"]["po_no"] == "PO-001"
    assert calls["create_invoice"]["vendor_tax_id"] == "12345678"
    assert calls["create_invoice"]["access_token"] == "test-access-token"
    assert calls["create_invoice"]["items"] == [
        {
            "line_no": 1,
            "item_name": "Laptop",
            "qty": 2.0,
            "unit_price": 500.0,
            "line_amount": 1000.0,
        }
    ]
    assert calls["create_invoice"]["ocr_parsed_json"]["taxId"] == "12345678"


@pytest.mark.asyncio
async def test_goods_receipt_submit_rejects_unapproved_po(client, monkeypatch):
    monkeypatch.setattr(
        employee_service.supabase_document_service,
        "list_approved_purchase_orders",
        lambda access_token=None: [{"poNo": "PO-OTHER"}],
    )

    async with client as c:
        response = await c.post(
            "/api/employee/goods-receipts",
            data={"grData": json.dumps(gr_payload())},
            files={"grFile": ("gr.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "poNo must reference an approved purchase order"


@pytest.mark.asyncio
async def test_invoice_submit_rejects_unapproved_po(client, monkeypatch):
    monkeypatch.setattr(
        employee_service.supabase_document_service,
        "list_approved_purchase_orders",
        lambda access_token=None: [{"poNo": "PO-OTHER"}],
    )

    async with client as c:
        response = await c.post(
            "/api/employee/invoices",
            data={"invoiceData": json.dumps(invoice_payload())},
            files={"invoiceFile": ("inv.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "poNo must reference an approved purchase order"


@pytest.mark.asyncio
async def test_ocr_rejects_unsupported_file_type(client):
    async with client as c:
        response = await c.post(
            "/api/employee/purchase-orders/ocr",
            files={"poFile": ("po.txt", b"not a pdf", "text/plain")},
        )

    assert response.status_code == 415
    assert response.json()["detail"] == "Only JPG, PNG, and PDF files are supported"


@pytest.mark.asyncio
async def test_submit_rejects_invalid_json(client):
    async with client as c:
        response = await c.post(
            "/api/employee/purchase-orders",
            data={"poData": "{"},
            files={"poFile": ("po.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invoice_submit_requires_tax_id(client):
    payload = invoice_payload()
    payload.pop("taxId")

    async with client as c:
        response = await c.post(
            "/api/employee/invoices",
            data={"invoiceData": json.dumps(payload)},
            files={"invoiceFile": ("inv.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_rolls_back_uploaded_file_when_rpc_fails(client, monkeypatch, calls):
    def fail_create_purchase_order(**kwargs):
        calls["create_purchase_order"] = kwargs
        raise RuntimeError("database unavailable")

    def fake_remove_from_storage(bucket_id, storage_path):
        calls.setdefault("removals", []).append((bucket_id, storage_path))

    monkeypatch.setattr(employee_service.supabase_document_service, "create_purchase_order", fail_create_purchase_order)
    monkeypatch.setattr(employee_service.document_storage_service, "remove_from_storage", fake_remove_from_storage)

    async with client as c:
        response = await c.post(
            "/api/employee/purchase-orders",
            data={"poData": json.dumps(po_payload())},
            files={"poFile": ("po.pdf", b"%PDF", "application/pdf")},
        )

    assert response.status_code == 500
    assert "Create purchase order failed" in response.json()["detail"]
    assert calls["removals"] == [("documents", "purchase_order/PO-001/po.pdf")]


def test_employee_create_rpcs_use_official_supabase_functions(monkeypatch):
    rpc_calls = []
    monkeypatch.setattr(
        supabase_document_service,
        "get_supabase_client_for_access_token",
        lambda access_token: FakeSupabaseClient(rpc_calls),
    )

    common_file = {
        "bucket_id": "documents",
        "storage_path": "path/doc.pdf",
        "original_filename": "doc.pdf",
        "file_type": "pdf",
        "file_size": 4,
    }

    supabase_document_service.create_purchase_order(
        vendor_tax_id="12345678",
        vendor_name="Vendor",
        po_no="PO-001",
        order_date="2026-05-01",
        total_amount=1000,
        items=[],
        files=[common_file],
        access_token="token",
    )
    supabase_document_service.create_goods_receipt(
        po_no="PO-001",
        gr_no="GR-001",
        received_date="2026-05-03",
        items=[],
        files=[common_file],
        access_token="token",
    )
    supabase_document_service.create_invoice(
        invoice_no="INV-001",
        invoice_date="2026-05-04",
        total_amount=1000,
        vendor_name="Vendor",
        vendor_tax_id="12345678",
        po_no="PO-001",
        items=[],
        ocr_parsed_json={},
        files=[common_file],
        access_token="token",
    )

    assert [name for name, _payload in rpc_calls] == [
        "employee_create_purchase_order",
        "employee_create_goods_receipt",
        "employee_create_invoice",
    ]
    assert rpc_calls[0][1]["p_vendor_tax_id"] == "12345678"
    assert "p_requester_user_id" not in rpc_calls[0][1]
    assert "p_received_by" not in rpc_calls[1][1]
    assert rpc_calls[2][1]["p_vendor_tax_id"] == "12345678"
    assert "p_employee_id" not in rpc_calls[2][1]


def test_employee_resubmit_invoice_uses_official_supabase_function(monkeypatch):
    rpc_calls = []
    monkeypatch.setattr(
        supabase_document_service,
        "get_supabase_client_for_access_token",
        lambda access_token: FakeSupabaseClient(rpc_calls),
    )

    supabase_document_service.resubmit_invoice(
        invoice_no="INV-001",
        invoice_data={"invoiceNo": "INV-001", "totalAmount": 2000},
        access_token="token",
    )

    assert rpc_calls == [
        ("employee_resubmit_invoice", {
            "p_invoice_no": "INV-001",
            "p_invoice_data": {"invoiceNo": "INV-001", "totalAmount": 2000},
        })
    ]
