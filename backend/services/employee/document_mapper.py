from __future__ import annotations


def first_present(*values):
    for value in values:
        if value is not None and value != "":
            return value
    return None


def to_int(value):
    try:
        return int(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def to_float(value):
    try:
        return float(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _line_no(item: dict, index: int) -> int:
    return to_int(first_present(item.get("lineNo"), item.get("line_no"), item.get("item_no"))) or index + 1


def normalize_po_items(items: list[dict]) -> list[dict]:
    normalized = []
    for index, item in enumerate(items):
        normalized.append(
            {
                "line_no": _line_no(item, index),
                "item_name": item.get("itemName"),
                "spec": item.get("spec"),
                "qty": to_float(item.get("quantity")),
                "unit_price": to_float(item.get("unitPrice")),
                "line_amount": to_float(item.get("lineAmount")),
            }
        )
    return normalized


def normalize_gr_items(items: list[dict]) -> list[dict]:
    normalized = []
    for index, item in enumerate(items):
        normalized.append(
            {
                "line_no": _line_no(item, index),
                "item_name": item.get("itemName"),
                "received_qty": to_float(item.get("receivedQty")),
                "accepted_qty": to_float(item.get("acceptedQty")),
                "line_amount": to_float(item.get("lineAmount")),
            }
        )
    return normalized


def normalize_invoice_items(items: list[dict]) -> list[dict]:
    normalized = []
    for index, item in enumerate(items):
        quantity = to_float(item.get("quantity"))
        unit_price = to_float(item.get("unitPrice"))
        line_amount = to_float(item.get("lineAmount"))
        if line_amount is None and quantity is not None and unit_price is not None:
            line_amount = quantity * unit_price
        normalized.append(
            {
                "line_no": _line_no(item, index),
                "item_name": item.get("itemName"),
                "qty": quantity,
                "unit_price": unit_price,
                "line_amount": line_amount,
            }
        )
    return normalized


def build_requisition_ocr_response(parsed: dict) -> dict:
    return {
        "doc_type": parsed["doc_type"],
        "applicant": parsed.get("applicant"),
        "requisition_date": parsed.get("requisition_date"),
        "requisition_no": parsed.get("requisition_no"),
        "department": parsed.get("department"),
        "company_name": parsed.get("company_name"),
        "vendor_no": parsed.get("vendor_no"),
        "total_amount": parsed.get("total_amount"),
        "items": parsed.get("items", []),
    }


def build_purchase_order_ocr_response(parsed: dict) -> dict:
    aligned_items = []
    for item in parsed.get("items", []):
        line_no = to_int(item.get("item_no"))
        qty = item.get("quantity")
        line_amount = item.get("subtotal")
        unit_price = round(line_amount / qty, 2) if qty and line_amount and qty > 0 else None

        aligned_items.append(
            {
                "lineNo": line_no,
                "itemName": item.get("name"),
                "spec": item.get("spec"),
                "quantity": qty,
                "unitPrice": unit_price,
                "lineAmount": line_amount,
            }
        )

    return {
        "poNo": parsed.get("po_number"),
        "purchaser": parsed.get("purchaser"),
        "department": parsed.get("department"),
        "vendorName": parsed.get("vendor_name"),
        "taxId": parsed.get("tax_id"),
        "poDate": parsed.get("order_date"),
        "totalAmount": parsed.get("total_amount"),
        "items": aligned_items,
    }


def build_invoice_ocr_response(parsed: dict) -> dict:
    return {
        "invoiceNo": parsed.get("invoice_number"),
        "poNo": parsed.get("po_number"),
        "invoiceDate": parsed.get("date"),
        "vendorName": parsed.get("vendor_name"),
        "totalAmount": parsed.get("total_amount"),
        "items": [
            {
                "lineNo": index + 1,
                "itemName": item.get("name"),
                "quantity": item.get("quantity"),
                "unitPrice": item.get("unit_price"),
            }
            for index, item in enumerate(parsed.get("items", []))
        ],
    }


def build_goods_receipt_ocr_response(parsed: dict) -> dict:
    aligned_items = []
    for item in parsed.get("items", []):
        line_no = to_int(item.get("item_no"))
        received_qty = item.get("quantity")
        aligned_items.append(
            {
                "lineNo": line_no,
                "itemName": item.get("name"),
                "receivedQty": received_qty,
                "acceptedQty": received_qty,
                "lineAmount": item.get("amount"),
            }
        )

    return {
        "grNo": parsed.get("gr_no"),
        "poNo": parsed.get("po_number"),
        "applicant": parsed.get("applicant"),
        "receiver": parsed.get("receiver"),
        "grDate": parsed.get("receipt_date"),
        "totalQty": parsed.get("total_qty"),
        "totalAmount": parsed.get("total_amount"),
        "items": aligned_items,
    }
