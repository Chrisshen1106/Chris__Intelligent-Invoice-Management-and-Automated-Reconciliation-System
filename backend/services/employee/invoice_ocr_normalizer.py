from __future__ import annotations

import re
from datetime import date
from typing import Any

_DIGIT_CONFUSABLES = str.maketrans({
    "O": "0",
    "o": "0",
    "I": "1",
    "l": "1",
    "|": "1",
})


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_digit_text(value: Any) -> str:
    return _clean_text(value).replace(",", "").replace(" ", "").translate(_DIGIT_CONFUSABLES)


def _number(value: Any) -> float | None:
    if value is None:
        return None
    text = _normalize_digit_text(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _int_text(value: Any) -> str | None:
    text = _normalize_digit_text(value)
    match = re.fullmatch(r"\d{8}", text)
    return match.group(0) if match else None


def _normalize_invoice_no_text(value: Any) -> str | None:
    text = _clean_text(value).replace(" ", "").replace("-", "").upper()
    match = re.fullmatch(r"([A-Z]{2})([0-9OoIl|]{8,9})", text)
    if not match:
        return None
    return match.group(1) + match.group(2).translate(_DIGIT_CONFUSABLES)


def _invoice_no_candidates_from_text(value: Any) -> list[str]:
    text = _clean_text(value).replace(" ", "").replace("-", "").upper()
    pattern = re.compile(r"(?<![A-Z0-9])([A-Z]{2}[0-9OoIl|]{8,9})(?![A-Z0-9])")
    return [
        normalized
        for match in pattern.finditer(text)
        if (normalized := _normalize_invoice_no_text(match.group(1)))
    ]


def _group_rows(tokens: list[dict], tolerance: float = 18) -> list[list[dict]]:
    usable = [
        token
        for token in tokens
        if _clean_text(token.get("text"))
        and isinstance(token.get("x"), int | float)
        and isinstance(token.get("y"), int | float)
    ]
    usable.sort(key=lambda item: (float(item["y"]), float(item["x"])))

    rows: list[list[dict]] = []
    for token in usable:
        if rows and abs(float(token["y"]) - float(rows[-1][0]["y"])) <= tolerance:
            rows[-1].append(token)
        else:
            rows.append([token])

    for row in rows:
        row.sort(key=lambda item: float(item["x"]))
    return rows


def _parse_invoice_no(text: str, tokens: list[dict]) -> str | None:
    candidates = []
    for token in tokens:
        for value in _invoice_no_candidates_from_text(token.get("text")):
            candidates.append((float(token.get("y") or 999999), value))

    for row in _group_rows(tokens):
        row_text = "".join(_clean_text(token.get("text")) for token in row)
        for value in _invoice_no_candidates_from_text(row_text):
            candidates.append((float(row[0].get("y") or 999999), value))

    if candidates:
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    fallback_candidates = _invoice_no_candidates_from_text(text)
    return fallback_candidates[0] if fallback_candidates else None




def _parse_invoice_date(text: str) -> str | None:
    roc_match = re.search(
        r"(?:中華民國|民國)?\s*(\d{2,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
        text,
    )
    if roc_match:
        year = int(roc_match.group(1)) + 1911
        month = int(roc_match.group(2))
        day = int(roc_match.group(3))
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None

    western_match = re.search(r"(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})", text)
    if western_match:
        year, month, day = (int(part) for part in western_match.groups())
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None
    return None


def _parse_seller_name(rows: list[list[dict]]) -> str | None:
    for row in rows:
        row_text = " ".join(_clean_text(token.get("text")) for token in row)
        if "賣" not in row_text or "方" not in row_text:
            continue
        company_tokens = [
            _clean_text(token.get("text"))
            for token in row
            if "公司" in _clean_text(token.get("text"))
        ]
        if company_tokens:
            return company_tokens[-1]
    return None


def _parse_seller_tax_id(rows: list[list[dict]]) -> str | None:
    seller_seen = False
    for row in rows:
        row_text = " ".join(_clean_text(token.get("text")) for token in row)
        if "賣" in row_text and "方" in row_text:
            seller_seen = True
            continue
        if not seller_seen:
            continue
        if "統" not in row_text and "編" not in row_text:
            continue
        for token in reversed(row):
            tax_id = _int_text(token.get("text"))
            if tax_id:
                return tax_id
    return None


def _parse_total_amount(rows: list[list[dict]]) -> float | None:
    for label in ("總計", "總金額", "應稅銷售額合計"):
        for row in rows:
            row_text = " ".join(_clean_text(token.get("text")) for token in row)
            if label not in row_text:
                continue
            numbers = [_number(token.get("text")) for token in row]
            numbers = [value for value in numbers if value is not None]
            if numbers:
                return numbers[-1]
    return None


def _nearest_number(row: list[dict], target_x: float, *, max_distance: float = 70) -> float | None:
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


def _find_invoice_table(rows: list[list[dict]]) -> dict | None:
    header_positions: dict[str, float] = {}
    header_aliases = {
        "name": ("品名", "名稱"),
        "quantity": ("數量",),
        "unitPrice": ("單價",),
        "amount": ("金額", "小計"),
    }

    for index, row in enumerate(rows):
        for token in row:
            text = _clean_text(token.get("text"))
            for field, aliases in header_aliases.items():
                if any(alias in text for alias in aliases):
                    header_positions[field] = float(token["x"])
        if {"name", "quantity", "unitPrice"}.issubset(header_positions):
            return {
                "header_row_index": index,
                "header_positions": header_positions,
            }

    return None


def _invoice_table_records(rows: list[list[dict]], table: dict) -> list[dict]:
    header_positions = table["header_positions"]
    amount_x = header_positions.get("amount")
    stop_keywords = ("銷售額", "合計", "營業稅", "總計", "賣", "方", "第一聯")
    records: list[dict] = []
    for row in rows[table["header_row_index"] + 1:]:
        row_text = " ".join(_clean_text(token.get("text")) for token in row)
        if any(keyword in row_text for keyword in stop_keywords):
            break

        quantity = _nearest_number(row, header_positions["quantity"])
        unit_price = _nearest_number(row, header_positions["unitPrice"])
        line_amount = _nearest_number(row, amount_x, max_distance=95) if amount_x is not None else None
        name_tokens = [
            _clean_text(token.get("text"))
            for token in row
            if float(token.get("x") or 0) <= header_positions["quantity"] - 40
            and re.search(r"[\u4e00-\u9fffA-Za-z]", _clean_text(token.get("text")))
        ]
        item_name = " ".join(name_tokens).strip()

        if not item_name and quantity is None and unit_price is None and line_amount is None:
            continue

        records.append(
            {
                "lineNo": len(records) + 1,
                "itemName": item_name or None,
                "quantity": quantity,
                "unitPrice": unit_price,
                "lineAmount": line_amount,
                "rawText": row_text,
            }
        )

    return records


def _markdown_table(records: list[dict]) -> str:
    if not records:
        return ""

    headers = ["lineNo", "itemName", "quantity", "unitPrice", "lineAmount", "rawText"]
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


def build_invoice_table_context(tokens: list[dict]) -> dict:
    rows = _group_rows(tokens)
    table = _find_invoice_table(rows)
    if not table:
        return {"tables": []}

    records = _invoice_table_records(rows, table)
    if not records:
        return {"tables": []}

    return {
        "tables": [
            {
                "name": "invoice_line_items",
                "headers": ["lineNo", "itemName", "quantity", "unitPrice", "lineAmount"],
                "markdown": _markdown_table(records),
                "rows": records,
            }
        ]
    }


def _parse_items(rows: list[list[dict]]) -> list[dict]:
    table = _find_invoice_table(rows)
    if not table:
        return []

    records = _invoice_table_records(rows, table)
    items: list[dict] = []
    for record in records:
        item_name = record.get("itemName")
        quantity = record.get("quantity")
        unit_price = record.get("unitPrice")
        line_amount = record.get("lineAmount")

        if not item_name or quantity is None or unit_price is None:
            continue
        if line_amount is not None and abs((quantity * unit_price) - line_amount) > 1:
            # The table parser is meant to prevent column shifts. If the math does
            # not match, skip this row instead of confidently returning bad data.
            continue

        items.append(
            {
                "lineNo": len(items) + 1,
                "itemName": item_name,
                "quantity": quantity,
                "unitPrice": unit_price,
            }
        )

    return items


def normalize_invoice_ocr_response(parsed: dict, merged_text: str, tokens: list[dict]) -> dict:
    """Correct invoice fields that are safer to derive from OCR geometry than LLM text."""
    if not isinstance(parsed, dict):
        return parsed

    rows = _group_rows(tokens)
    normalized = dict(parsed)

    invoice_no = _parse_invoice_no(merged_text, tokens)
    if invoice_no:
        normalized["invoiceNo"] = invoice_no

    invoice_date = _parse_invoice_date(merged_text)
    if invoice_date:
        normalized["invoiceDate"] = invoice_date

    seller_name = _parse_seller_name(rows)
    if seller_name:
        normalized["vendorName"] = seller_name

    seller_tax_id = _parse_seller_tax_id(rows)
    if seller_tax_id:
        normalized["taxId"] = seller_tax_id

    total_amount = _parse_total_amount(rows)
    if total_amount is not None:
        normalized["totalAmount"] = total_amount

    items = _parse_items(rows)
    if items:
        normalized["items"] = items

    normalized["poNo"] = None
    return normalized
