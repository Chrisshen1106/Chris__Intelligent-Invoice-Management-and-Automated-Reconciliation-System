from __future__ import annotations

from itertools import product
import re
from datetime import date
from typing import Any

from services.employee.invoice_ocr_normalizer import _clean_text, _group_rows, _number


def _markdown_table(records: list[dict], headers: list[str]) -> str:
    if not records:
        return ""
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for record in records:
        lines.append(
            "| "
            + " | ".join(
                "" if record.get(header) is None else str(record.get(header)).replace("|", "/")
                for header in headers
            )
            + " |"
        )
    return "\n".join(lines)


def _find_header_table(rows: list[list[dict]], header_aliases: dict[str, tuple[str, ...]], required: set[str]) -> dict | None:
    header_positions: dict[str, float] = {}
    for index, row in enumerate(rows):
        for token in row:
            text = _clean_text(token.get("text"))
            for field, aliases in header_aliases.items():
                if any(alias in text for alias in aliases):
                    header_positions[field] = float(token["x"])
        if required.issubset(header_positions):
            return {
                "header_row_index": index,
                "header_positions": header_positions,
            }
    return None


def _nearest_number(row: list[dict], target_x: float, *, max_distance: float = 80) -> float | None:
    candidates = []
    for token in row:
        value = _number(token.get("text"))
        if value is None:
            continue
        distance = abs(float(token.get("x") or 0) - target_x)
        if distance <= max_distance:
            candidates.append((distance, value))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _nearest_text(row: list[dict], target_x: float, *, max_distance: float = 90) -> str | None:
    candidates = []
    for token in row:
        text = _clean_text(token.get("text"))
        if not text:
            continue
        distance = abs(float(token.get("x") or 0) - target_x)
        if distance <= max_distance:
            candidates.append((distance, text))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _item_name_before(row: list[dict], boundary_x: float, *, after_x: float | None = None) -> str | None:
    tokens = []
    for token in row:
        x = float(token.get("x") or 0)
        text = _clean_text(token.get("text"))
        if not text:
            continue
        if after_x is not None and x <= after_x:
            continue
        if x >= boundary_x:
            continue
        if re.search(r"[\u4e00-\u9fffA-Za-z]", text):
            tokens.append(text)
    return " ".join(tokens).strip() or None


def _value_after_label(rows: list[list[dict]], label: str) -> str | None:
    for row in rows:
        for index, token in enumerate(row):
            if label not in _clean_text(token.get("text")):
                continue
            if index + 1 < len(row):
                return _clean_text(row[index + 1].get("text")) or None
    return None


def _parse_purchase_order_no(rows: list[list[dict]]) -> str | None:
    po_pattern = re.compile(r"^PO[-A-Za-z0-9]+$")
    for row in rows:
        candidates = [
            (float(token.get("x") or 0), _clean_text(token.get("text")).replace(" ", ""))
            for token in row
            if po_pattern.fullmatch(_clean_text(token.get("text")).replace(" ", ""))
        ]
        if len(candidates) >= 2:
            candidates.sort(key=lambda item: item[0])
            return candidates[-1][1]

    candidates = []
    for row in rows:
        for token in row:
            value = _clean_text(token.get("text")).replace(" ", "")
            if po_pattern.fullmatch(value):
                digits = sum(char.isdigit() for char in value)
                candidates.append((digits, len(value), float(token.get("x") or 0), value))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][3]


def _date_value(value: Any) -> str | None:
    text = _clean_text(value)
    match = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", text)
    if not match:
        match = re.search(r"(\d{4})(\d{2})(\d{2})", text)
    if not match:
        return None
    year, month, day = (int(part) for part in match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _eight_digit_text(value: Any) -> str | None:
    text = _clean_text(value).replace(" ", "").translate(str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "|": "1"}))
    match = re.fullmatch(r"\d{8}", text)
    return match.group(0) if match else None


def _parse_total(rows: list[list[dict]], labels: tuple[str, ...]) -> float | None:
    for row in rows:
        row_text = " ".join(_clean_text(token.get("text")) for token in row)
        if not any(label in row_text for label in labels):
            continue
        numbers = [_number(token.get("text")) for token in row]
        numbers = [value for value in numbers if value is not None]
        if numbers:
            return numbers[-1]
    return None


def _purchase_order_records(rows: list[list[dict]]) -> list[dict]:
    table = _find_header_table(
        rows,
        {
            "lineNo": ("項次",),
            "itemName": ("品名",),
            "unitPrice": ("單價",),
            "quantity": ("數量",),
            "spec": ("規格",),
            "lineAmount": ("小計", "金額"),
        },
        {"itemName", "unitPrice", "quantity", "lineAmount"},
    )
    if not table:
        return []

    positions = table["header_positions"]
    records: list[dict] = []
    for row in rows[table["header_row_index"] + 1:]:
        row_text = " ".join(_clean_text(token.get("text")) for token in row)
        if any(keyword in row_text for keyword in ("採購合計", "合計", "備註")):
            break

        line_no = _nearest_number(row, positions.get("lineNo", 0), max_distance=80)
        item_name = _item_name_before(row, positions["unitPrice"], after_x=positions.get("lineNo"))
        unit_price = _nearest_number(row, positions["unitPrice"])
        quantity = _nearest_number(row, positions["quantity"])
        spec = _nearest_text(row, positions.get("spec", 0), max_distance=110) if "spec" in positions else None
        line_amount = _nearest_number(row, positions["lineAmount"], max_distance=100)

        if not item_name and quantity is None and unit_price is None and line_amount is None:
            continue

        records.append(
            {
                "lineNo": int(line_no) if line_no is not None else len(records) + 1,
                "itemName": item_name,
                "spec": spec,
                "quantity": quantity,
                "unitPrice": unit_price,
                "lineAmount": line_amount,
                "rawText": row_text,
            }
        )
    return records


def build_purchase_order_table_context(tokens: list[dict]) -> dict:
    rows = _group_rows(tokens)
    records = _purchase_order_records(rows)
    if not records:
        return {"tables": []}
    headers = ["lineNo", "itemName", "spec", "quantity", "unitPrice", "lineAmount", "rawText"]
    return {
        "tables": [
            {
                "name": "purchase_order_line_items",
                "headers": headers[:-1],
                "markdown": _markdown_table(records, headers),
                "rows": records,
            }
        ]
    }


def normalize_purchase_order_ocr_response(parsed: dict, merged_text: str, tokens: list[dict]) -> dict:
    if not isinstance(parsed, dict):
        return parsed

    rows = _group_rows(tokens)
    normalized = dict(parsed)

    po_no = _parse_purchase_order_no(rows) or _value_after_label(rows, "採購單號")
    if po_no:
        normalized["poNo"] = po_no
    purchaser = _value_after_label(rows, "採購人員")
    if purchaser:
        normalized["purchaser"] = purchaser
    department = _value_after_label(rows, "採購部門")
    if department:
        normalized["department"] = department
    vendor_name = _value_after_label(rows, "供應商名稱")
    if vendor_name:
        normalized["vendorName"] = vendor_name
    tax_id = _eight_digit_text(_value_after_label(rows, "統一編號"))
    if tax_id:
        normalized["taxId"] = tax_id
    po_date = _date_value(_value_after_label(rows, "採購日期"))
    if po_date:
        normalized["poDate"] = po_date
    total = _parse_total(rows, ("採購合計", "合計"))
    if total is not None:
        normalized["totalAmount"] = total

    records = _purchase_order_records(rows)
    items = []
    for record in records:
        quantity = record.get("quantity")
        unit_price = record.get("unitPrice")
        line_amount = record.get("lineAmount")
        if not record.get("itemName") or quantity is None or unit_price is None:
            continue
        if line_amount is not None and abs(quantity * unit_price - line_amount) > 1:
            continue
        items.append(
            {
                "lineNo": len(items) + 1,
                "itemName": record.get("itemName"),
                "spec": record.get("spec"),
                "quantity": quantity,
                "unitPrice": unit_price,
                "lineAmount": line_amount if line_amount is not None else quantity * unit_price,
            }
        )
    if items:
        normalized["items"] = items
    return normalized


def _goods_receipt_records(rows: list[list[dict]]) -> list[dict]:
    table = _find_header_table(
        rows,
        {
            "lineNo": ("項次",),
            "itemName": ("品名",),
            "receivedQty": ("收貨數量", "數量"),
            "lineAmount": ("金額", "小計"),
        },
        {"itemName", "receivedQty", "lineAmount"},
    )
    if not table:
        return []

    positions = table["header_positions"]
    records: list[dict] = []
    for row in rows[table["header_row_index"] + 1:]:
        row_text = " ".join(_clean_text(token.get("text")) for token in row)
        if any(keyword in row_text for keyword in ("驗收數量", "合格數量", "合計", "驗收人簽名")):
            break

        line_no = _nearest_number(row, positions.get("lineNo", 0), max_distance=80)
        item_name = _item_name_before(row, positions["receivedQty"], after_x=positions.get("lineNo"))
        received_qty = _nearest_number(row, positions["receivedQty"])
        line_amount = _nearest_number(row, positions["lineAmount"], max_distance=120)

        if not item_name and received_qty is None and line_amount is None:
            continue

        records.append(
            {
                "lineNo": int(line_no) if line_no is not None else len(records) + 1,
                "itemName": item_name,
                "receivedQty": received_qty,
                "acceptedQty": received_qty,
                "lineAmount": line_amount,
                "rawText": row_text,
            }
        )
    return records


def _reconcile_goods_receipt_line_amounts(records: list[dict], total_amount: float | None) -> list[dict]:
    if total_amount is None or not records or len(records) > 8:
        return records

    choices = []
    for record in records:
        received_qty = record.get("receivedQty")
        line_amount = record.get("lineAmount")
        if received_qty is None or line_amount is None:
            choices.append((line_amount,))
            continue
        multiplied = received_qty * line_amount
        if abs(multiplied - line_amount) <= 1:
            choices.append((line_amount,))
        else:
            choices.append((line_amount, multiplied))

    for candidate in product(*choices):
        if any(value is None for value in candidate):
            continue
        if abs(sum(candidate) - total_amount) <= 1:
            reconciled = [dict(record) for record in records]
            for record, value in zip(reconciled, candidate):
                record["lineAmount"] = value
            return reconciled
    return records


def _filter_goods_receipt_summary_items(
    items: Any,
    *,
    asset_kind: str | None,
    total_qty: float | None,
    total_amount: float | None,
) -> list[dict]:
    if not isinstance(items, list):
        return []

    filtered = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_name = _clean_text(item.get("itemName"))
        received_qty = _number(item.get("receivedQty"))
        accepted_qty = _number(item.get("acceptedQty"))
        line_amount = _number(item.get("lineAmount"))
        looks_like_asset_summary = (
            asset_kind
            and item_name == asset_kind
            and total_qty is not None
            and total_amount is not None
            and received_qty is not None
            and line_amount is not None
            and abs(received_qty - total_qty) <= 1
            and abs(line_amount - total_amount) <= 1
        )
        if looks_like_asset_summary:
            continue
        if item_name in {"驗收數量", "合格數量", "合計", "資產種類"}:
            continue
        filtered.append(item)
    return filtered


def build_goods_receipt_table_context(tokens: list[dict]) -> dict:
    rows = _group_rows(tokens)
    records = _goods_receipt_records(rows)
    if not records:
        return {"tables": []}
    headers = ["lineNo", "itemName", "receivedQty", "acceptedQty", "lineAmount", "rawText"]
    return {
        "tables": [
            {
                "name": "goods_receipt_line_items",
                "headers": headers[:-1],
                "markdown": _markdown_table(records, headers),
                "rows": records,
            }
        ]
    }


def normalize_goods_receipt_ocr_response(parsed: dict, merged_text: str, tokens: list[dict]) -> dict:
    if not isinstance(parsed, dict):
        return parsed

    rows = _group_rows(tokens)
    normalized = dict(parsed)

    gr_no = _value_after_label(rows, "驗收單號")
    if gr_no:
        normalized["grNo"] = gr_no
    applicant = _value_after_label(rows, "採購申請人")
    if applicant:
        normalized["applicant"] = applicant
    receiver = _value_after_label(rows, "驗收人")
    if receiver:
        normalized["receiver"] = receiver
    gr_date = _date_value(_value_after_label(rows, "到貨日期")) or _date_value(_value_after_label(rows, "驗收日期"))
    if gr_date:
        normalized["grDate"] = gr_date
    total_qty = _parse_total(rows, ("驗收數量",))
    if total_qty is not None:
        normalized["totalQty"] = total_qty
    total = _parse_total(rows, ("合計",))
    if total is not None:
        normalized["totalAmount"] = total

    asset_kind = _value_after_label(rows, "資產種類")
    records = _reconcile_goods_receipt_line_amounts(_goods_receipt_records(rows), normalized.get("totalAmount"))
    items = []
    for record in records:
        if not record.get("itemName") or record.get("receivedQty") is None:
            continue
        items.append(
            {
                "lineNo": len(items) + 1,
                "itemName": record.get("itemName"),
                "receivedQty": record.get("receivedQty"),
                "acceptedQty": record.get("acceptedQty"),
                "lineAmount": record.get("lineAmount"),
            }
        )
    if items:
        normalized["items"] = items
    else:
        normalized["items"] = _filter_goods_receipt_summary_items(
            normalized.get("items"),
            asset_kind=asset_kind,
            total_qty=normalized.get("totalQty"),
            total_amount=normalized.get("totalAmount"),
        )
    return normalized
