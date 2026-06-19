import pytest
from httpx import ASGITransport, AsyncClient

from core.auth import get_current_access_token, get_current_user
from main import app
from services.finance import finance_service
from services.integrations import supabase_document_service


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: "finance-user"
    app.dependency_overrides[get_current_access_token] = lambda: "finance-access-token"
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def calls():
    return {}


def _file_metadata(file_type: str = "pdf"):
    return {
        "bucketId": "documents",
        "storagePath": "purchase_orders/PO-001/file.pdf",
        "originalFilename": "file.pdf",
        "fileType": file_type,
    }


@pytest.mark.asyncio
async def test_3_1_get_pending_purchase_orders(client, monkeypatch):
    monkeypatch.setattr(
        finance_service.supabase_document_service,
        "list_pending_purchase_orders",
        lambda access_token=None: [
            {
                "po_id": "po-id",
                "po_no": "PO-001",
                "requester": {"name": "Alice", "department": "IT"},
                "vendor": {"name": "Vendor"},
                "order_date": "2026-05-01",
                "total_amount": 1000,
                "created_at": "2026-05-02T10:00:00Z",
            }
        ],
    )

    async with client as c:
        response = await c.get("/api/finance/purchase-orders/pending")

    assert response.status_code == 200
    assert response.json() == [
        {
            "poId": "po-id",
            "poNo": "PO-001",
            "purchaser": "Alice",
            "department": "IT",
            "vendorName": "Vendor",
            "poDate": "2026-05-01",
            "totalAmount": 1000,
            "submittedAt": "2026-05-02T10:00:00Z",
        }
    ]


@pytest.mark.asyncio
async def test_3_2_get_purchase_order_detail(client, monkeypatch):
    monkeypatch.setattr(
        finance_service.supabase_document_service,
        "get_purchase_order_detail",
        lambda po_no, access_token=None: {
            "id": "po-id",
            "po_no": po_no,
            "requester": {"name": "Alice", "department": "IT"},
            "vendor": {"name": "Vendor", "tax_id": "12345678"},
            "order_date": "2026-05-01",
            "total_amount": 1000,
            "items": [
                {
                    "line_no": 1,
                    "item_name": "Laptop",
                    "spec": "14 inch",
                    "qty": 2,
                    "unit_price": 500,
                    "line_amount": 1000,
                }
            ],
        },
    )

    async with client as c:
        response = await c.get("/api/finance/purchase-orders/PO-001")

    assert response.status_code == 200
    assert response.json() == {
        "poId": "po-id",
        "poNo": "PO-001",
        "purchaser": "Alice",
        "department": "IT",
        "vendorName": "Vendor",
        "taxId": "12345678",
        "poDate": "2026-05-01",
        "totalAmount": 1000,
        "submittedBy": "Alice",
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


@pytest.mark.asyncio
async def test_3_3_get_purchase_order_file_returns_binary(client, monkeypatch, calls):
    monkeypatch.setattr(
        finance_service.supabase_document_service,
        "get_purchase_order_file",
        lambda po_no, access_token=None: _file_metadata(),
    )

    def fake_download(bucket_id, storage_path):
        calls["download"] = (bucket_id, storage_path)
        return b"%PDF-1.4"

    monkeypatch.setattr(finance_service.document_storage_service, "download_from_storage", fake_download)

    async with client as c:
        response = await c.get("/api/finance/purchase-orders/PO-001/file")

    assert response.status_code == 200
    assert response.content == b"%PDF-1.4"
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == "inline; filename*=utf-8''file.pdf"
    assert calls["download"] == ("documents", "purchase_orders/PO-001/file.pdf")


@pytest.mark.asyncio
async def test_3_4_review_purchase_order_approves(client, monkeypatch, calls):
    def fake_review_purchase_order(**kwargs):
        calls["review"] = kwargs
        return {"success": True, "poNo": kwargs["po_no"], "status": "approved"}

    monkeypatch.setattr(
        finance_service.supabase_document_service,
        "review_purchase_order",
        fake_review_purchase_order,
    )

    async with client as c:
        response = await c.post(
            "/api/finance/purchase-orders/PO-001/review",
            json={"actionType": 1, "rejectReason": None},
        )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "poNo": "PO-001",
        "status": "approved",
        "message": "Purchase order reviewed successfully",
    }
    assert calls["review"] == {
        "po_no": "PO-001",
        "decision": "approve",
        "comment": None,
        "access_token": "finance-access-token",
    }


@pytest.mark.asyncio
async def test_3_5_get_pending_match_groups(client, monkeypatch):
    monkeypatch.setattr(
        finance_service.supabase_document_service,
        "list_pending_match_groups",
        lambda access_token=None: [
            {
                "po_no": "PO-001",
                "vendor_name": "Vendor",
                "order_date": "2026-05-01",
                "invoice_no": "INV-001",
                "invoice_date": "2026-05-04",
                "gr_no": "GR-001",
                "total_amount": 1000,
                "group_status": "on_hold",
            }
        ],
    )

    async with client as c:
        response = await c.get("/api/finance/match-groups/pending")

    assert response.status_code == 200
    assert response.json() == [
        {
            "poNo": "PO-001",
            "vendorName": "Vendor",
            "poDate": "2026-05-01",
            "invoiceNo": "INV-001",
            "invoiceDate": "2026-05-04",
            "grNo": "GR-001",
            "totalAmount": 1000,
            "groupStatus": "onHold",
        }
    ]


@pytest.mark.asyncio
async def test_3_6_get_match_group_detail(client, monkeypatch):
    monkeypatch.setattr(
        finance_service.supabase_document_service,
        "get_match_group_detail",
        lambda po_no, access_token=None: {
            "poNo": po_no,
            "vendorName": "Vendor",
            "groupStatus": "pending",
            "po": {
                "poId": "po-id",
                "purchaser": "Alice",
                "department": "IT",
                "taxId": "12345678",
                "poDate": "2026-05-01",
                "totalAmount": 1000,
                "uploadedBy": "Alice",
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
            "gr": {
                "grId": "gr-id",
                "grNo": "GR-001",
                "applicant": "Alice",
                "receiver": "Bob",
                "grDate": "2026-05-03",
                "totalQty": 2,
                "totalAmount": 1000,
                "uploadedBy": "Bob",
                "items": [
                    {
                        "lineNo": 1,
                        "itemName": "Laptop",
                        "receivedQty": 2,
                        "acceptedQty": 2,
                        "lineAmount": 1000,
                    }
                ],
            },
            "invoice": {
                "invoiceId": "invoice-id",
                "invoiceNo": "INV-001",
                "invoiceDate": "2026-05-04",
                "totalAmount": 1000,
                "uploadedBy": "Cathy",
                "items": [{"lineNo": 1, "itemName": "Laptop", "quantity": 2, "unitPrice": 500}],
            },
            "comparisonItems": [
                {
                    "itemName": "Laptop",
                    "poQty": 2,
                    "poUnitPrice": 500,
                    "grQty": 2,
                    "grUnitPrice": 500,
                    "invoiceQty": 2,
                    "invoiceUnitPrice": 500,
                }
            ],
        },
    )

    async with client as c:
        response = await c.get("/api/finance/match-groups/PO-001")

    assert response.status_code == 200
    assert response.json()["poNo"] == "PO-001"
    assert response.json()["po"]["items"][0]["itemName"] == "Laptop"
    assert response.json()["gr"]["items"][0]["acceptedQty"] == 2
    assert response.json()["invoice"]["invoiceNo"] == "INV-001"
    assert response.json()["comparisonItems"][0]["invoiceUnitPrice"] == 500


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "expected_doc_type"),
    [
        ("/api/finance/match-groups/PO-001/po/file", "purchaseOrder"),
        ("/api/finance/match-groups/PO-001/gr/file", "goodsReceipt"),
        ("/api/finance/match-groups/PO-001/invoice/file", "invoice"),
    ],
)
async def test_3_7_to_3_9_get_match_group_files_return_binary(
    client,
    monkeypatch,
    calls,
    path,
    expected_doc_type,
):
    def fake_get_match_group_file(**kwargs):
        calls.setdefault("files", []).append(kwargs)
        return _file_metadata()

    monkeypatch.setattr(
        finance_service.supabase_document_service,
        "get_match_group_file",
        fake_get_match_group_file,
    )
    monkeypatch.setattr(
        finance_service.document_storage_service,
        "download_from_storage",
        lambda bucket_id, storage_path: b"%PDF-1.4",
    )

    async with client as c:
        response = await c.get(path)

    assert response.status_code == 200
    assert response.content == b"%PDF-1.4"
    assert response.headers["content-type"] == "application/pdf"
    assert calls["files"][-1] == {
        "po_no": "PO-001",
        "doc_type": expected_doc_type,
        "access_token": "finance-access-token",
    }


@pytest.mark.asyncio
async def test_3_10_approve_match_group(client, monkeypatch):
    monkeypatch.setattr(
        finance_service.supabase_document_service,
        "get_match_group_detail",
        lambda po_no, access_token=None: {
            "poNo": po_no,
            "po": {"totalAmount": 1000},
            "gr": {"totalAmount": 1000},
            "invoice": {"totalAmount": 1000},
            "comparisonItems": [
                {
                    "itemName": "Laptop",
                    "poQty": 2,
                    "poUnitPrice": 500,
                    "grQty": 2,
                    "grUnitPrice": 500,
                    "invoiceQty": 2,
                    "invoiceUnitPrice": 500,
                }
            ],
        },
    )
    monkeypatch.setattr(
        finance_service.supabase_document_service,
        "approve_match_group",
        lambda po_no, access_token=None: {"success": True, "po_no": po_no, "message": "approved"},
    )

    async with client as c:
        response = await c.post("/api/finance/match-groups/PO-001/approve")

    assert response.status_code == 200
    assert response.json() == {"success": True, "poNo": "PO-001", "message": "approved"}


@pytest.mark.asyncio
async def test_3_10_approve_match_group_rejects_total_mismatch(client, monkeypatch):
    monkeypatch.setattr(
        finance_service.supabase_document_service,
        "get_match_group_detail",
        lambda po_no, access_token=None: {
            "poNo": po_no,
            "po": {"totalAmount": 1000},
            "gr": {"totalAmount": 1000},
            "invoice": {"totalAmount": 2000},
            "comparisonItems": [
                {
                    "itemName": "Laptop",
                    "poQty": 2,
                    "poUnitPrice": 500,
                    "grQty": 2,
                    "grUnitPrice": 500,
                    "invoiceQty": 2,
                    "invoiceUnitPrice": 500,
                }
            ],
        },
    )

    async with client as c:
        response = await c.post("/api/finance/match-groups/PO-001/approve")

    assert response.status_code == 409
    assert "總金額不符" in response.json()["detail"]


@pytest.mark.asyncio
async def test_auto_review_match_group_holds_mismatched_group(client, monkeypatch, calls):
    monkeypatch.setattr(
        finance_service.supabase_document_service,
        "get_match_group_detail",
        lambda po_no, access_token=None: {
            "poNo": po_no,
            "po": {"totalAmount": 1000},
            "gr": {"totalAmount": 1000},
            "invoice": {"totalAmount": 2000},
            "comparisonItems": [
                {
                    "itemName": "Laptop",
                    "poQty": 2,
                    "poUnitPrice": 500,
                    "grQty": 2,
                    "grUnitPrice": 500,
                    "invoiceQty": 2,
                    "invoiceUnitPrice": 500,
                }
            ],
        },
    )

    def fake_hold_match_group(po_no, reason=None, access_token=None):
        calls["hold"] = {"po_no": po_no, "reason": reason, "access_token": access_token}
        return {"success": True, "po_no": po_no, "group_status": "onHold"}

    monkeypatch.setattr(
        finance_service.supabase_document_service,
        "hold_match_group",
        fake_hold_match_group,
    )

    async with client as c:
        response = await c.post("/api/finance/match-groups/PO-001/auto-review")

    assert response.status_code == 200
    body = response.json()
    assert body["matched"] is False
    assert body["groupStatus"] == "onHold"
    assert body["issues"][0]["code"] == "po_invoice_total_mismatch"
    assert "總金額不符" in calls["hold"]["reason"]


@pytest.mark.asyncio
async def test_3_11_reject_match_group_document(client, monkeypatch, calls):
    def fake_reject_match_group_document(**kwargs):
        calls["reject"] = kwargs
        return {"success": True, "po_no": kwargs["po_no"], "group_status": "on_hold"}

    monkeypatch.setattr(
        finance_service.supabase_document_service,
        "reject_match_group_document",
        fake_reject_match_group_document,
    )

    async with client as c:
        response = await c.post(
            "/api/finance/match-groups/PO-001/reject",
            json={"docType": "invoice", "rejectReason": "金額不符"},
        )

    assert response.status_code == 200
    assert response.json() == {"success": True, "poNo": "PO-001", "groupStatus": "onHold"}
    assert calls["reject"] == {
        "po_no": "PO-001",
        "doc_type": "invoice",
        "reject_reason": "金額不符",
        "access_token": "finance-access-token",
    }


@pytest.mark.asyncio
async def test_3_12_hold_match_group(client, monkeypatch):
    monkeypatch.setattr(
        finance_service.supabase_document_service,
        "hold_match_group",
        lambda po_no, reason=None, access_token=None: {"success": True, "po_no": po_no, "group_status": "onHold"},
    )

    async with client as c:
        response = await c.post("/api/finance/match-groups/PO-001/hold")

    assert response.status_code == 200
    assert response.json() == {"success": True}


@pytest.mark.asyncio
async def test_3_13_get_finance_logs(client, monkeypatch):
    monkeypatch.setattr(
        finance_service.supabase_document_service,
        "list_my_match_group_logs",
        lambda access_token=None: [
            {
                "acted_at": "2026-05-05 10:00:00",
                "po_no": "PO-001",
                "action_type": "reject",
                "doc_type": "invoice",
                "comment": "金額不符",
                "details": [{"field": "totalAmount"}],
            }
        ],
    )

    async with client as c:
        response = await c.get("/api/finance/logs")

    assert response.status_code == 200
    assert response.json() == [
        {
            "timestamp": "2026-05-05 10:00:00",
            "poNo": "PO-001",
            "actionType": "reject",
            "docType": "invoice",
            "remark": "金額不符",
            "details": [{"field": "totalAmount"}],
        }
    ]


class FakeRpcResult:
    data = {"ok": True}

    def execute(self):
        return self


class FakeSupabaseClient:
    def __init__(self, calls):
        self.calls = calls

    def rpc(self, function_name, payload):
        self.calls.append((function_name, payload))
        return FakeRpcResult()


def test_finance_rpcs_use_official_supabase_functions(monkeypatch):
    rpc_calls = []
    monkeypatch.setattr(
        supabase_document_service,
        "get_supabase_client_for_access_token",
        lambda access_token: FakeSupabaseClient(rpc_calls),
    )

    supabase_document_service.list_pending_purchase_orders(access_token="token")
    supabase_document_service.get_purchase_order_detail("PO-001", access_token="token")
    supabase_document_service.get_purchase_order_file("PO-001", access_token="token")
    supabase_document_service.review_purchase_order(
        po_no="PO-001",
        decision="approve",
        comment=None,
        access_token="token",
    )
    supabase_document_service.list_pending_match_groups(access_token="token")
    supabase_document_service.get_match_group_detail("PO-001", access_token="token")
    supabase_document_service.get_match_group_file(
        po_no="PO-001",
        doc_type="invoice",
        access_token="token",
    )
    supabase_document_service.approve_match_group("PO-001", access_token="token")
    supabase_document_service.reject_match_group_document(
        po_no="PO-001",
        doc_type="invoice",
        reject_reason="金額不符",
        access_token="token",
    )
    supabase_document_service.hold_match_group("PO-001", access_token="token")
    supabase_document_service.list_my_match_group_logs(access_token="token")

    assert [name for name, _payload in rpc_calls] == [
        "finance_get_pending_purchase_orders",
        "finance_get_purchase_order_detail",
        "finance_get_purchase_order_file",
        "finance_review_purchase_order",
        "finance_get_pending_match_groups",
        "finance_get_match_group_detail",
        "finance_get_match_group_file",
        "finance_approve_match_group",
        "finance_reject_match_group_document",
        "finance_hold_match_group",
        "finance_get_my_match_group_logs",
    ]
    assert rpc_calls[1][1] == {"p_po_no": "PO-001"}
    assert rpc_calls[3][1] == {"p_po_no": "PO-001", "p_decision": "approve", "p_comment": None}
    assert rpc_calls[6][1] == {"p_po_no": "PO-001", "p_doc_type": "invoice"}
    assert rpc_calls[9][1] == {"p_po_no": "PO-001", "p_reason": None}
    assert rpc_calls[8][1] == {
        "p_po_no": "PO-001",
        "p_doc_type": "invoice",
        "p_reject_reason": "金額不符",
    }
