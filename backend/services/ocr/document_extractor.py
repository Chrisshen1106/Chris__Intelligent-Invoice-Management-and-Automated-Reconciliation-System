from __future__ import annotations

import re
from typing import Any

# 共用工具
_SKIP_VALUES = {
    "品名", "合計", "總計", "備註", "採購單號", "請購單號", "請購編號", "請購编号",
    "探購單號", "探購单号", "探購單号", 
    "供應商名稱", "項次", "頂次", "數量", "單位","規格", "小計", "單價", "物料編號", "物料号",
    "請購數量", "請購金額", "請購金额", "公司名稱", "公司名", "廠商編號", "廠商号", "廠商號",
    "申請人", "請購日期", "請日期", "購日期", "請購部門", "請購部门", "請購号",
    "採購人員", "採購部門", "探購人員", "探購部門", 
    "供應商聯絡人", "供應商電話", "供應商地址","地址", "電話",
    "付款方式", "預計交貨日", "預計付款日", "統一編號", "統一號" 

    # ── 驗收單專屬雜訊 (新增「收人」、「收日期」等避險關鍵字) ──
    "採購申請人", "到貨日期", "驗收人", "收人", "資產種類", "合計件數", 
    "驗收合格數量", "验收合格数量", "驗收合格数量", "合格數量", "合格数量", "验收合格","驗收數量", "验收数量",  
    "驗收人簽名", "收人簽名", "簽名", "驗收日期", "收日期", "驗收單", "收單",

    #三聯式發票專屬雜訊
    "營業人蓋用統一發票專用章", "統一發票專用章", "發票專用章", 
    "銷售額合計", "營業稅", "免稅", "應稅", "零稅率",
    "存根聯", "扣抵聯", "收執聯", "第一聯", "第二聯", "第三聯", "金額"
}
_NOISE_TOKENS = {"偏", "備", "註"}


def _parse_date(text: str) -> str | None:
    m = re.search(
        r"(\d{2,4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"
        r"|(\d{2,4})[-/.](\d{1,2})[-/.](\d{1,2})",
        text
    )
    if not m:
        return None
    y, mo, d = (m.group(1), m.group(2), m.group(3)) if m.group(1) \
               else (m.group(4), m.group(5), m.group(6))
    year = int(y)
    if year < 200:
        year += 1911
    mo, d = mo.zfill(2), d.zfill(2)
    return f"{year}-{mo}-{d}" if 1 <= int(mo) <= 12 and 1 <= int(d) <= 31 else None


def _parse_amount(text: str) -> int | None:
    try:
        return int(str(text).replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _field_re(pattern: str, text: str, group: int = 1) -> str | None:
    """從 merged_text 用 regex 抓單一欄位值。"""
    m = re.search(pattern, text)
    return m.group(group).strip() if m else None



# Token-based 空間感知抓取
def _token_value_after_key(tokens: list[dict], key_substrings: list[str]) -> str | None:
    """
    透過 (x, y) 座標，尋找位於 key 右側最接近的 Token (允許 y 軸些微高低差)。
    若右側找不到，則尋找正下方。
    """
    key_token = None
    for t in tokens:
        if any(sub in t["text"] for sub in key_substrings):
            key_token = t
            break
            
    if not key_token:
        return None
        
    candidates = []
    below_candidates = []
    
    for t in tokens:
        if t == key_token or t["text"] in _NOISE_TOKENS or t["text"] in _SKIP_VALUES:
            continue
            
        dy = t["y"] - key_token["y"]
        dx = t["x"] - key_token["x"]
        
        # 1. 尋找同一行且在右側的 Token (y 誤差 < 25px)
        if abs(dy) < 25 and dx > 0:
            candidates.append((dx, t))
            
        # 2. 備用：尋找正下方的 Token (y 在下方 0~50px，x 對齊度 < 100px)
        elif 0 < dy < 50 and abs(dx) < 100:
            below_candidates.append((dy, t))
            
    if candidates:
        # 依照與 key 的水平距離 (dx) 排序，取最近的一個
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]["text"]
        
    if below_candidates:
        below_candidates.sort(key=lambda item: item[0])
        return below_candidates[0][1]["text"]
        
    return None

# 公開介面：供 main.py 在不區分單據類型時呼叫（通用測試用）
def extract_with_tokens(merged_text: str, tokens: list[dict]) -> dict:
    """僅供 /api/ocr 測試端點使用，回傳原始文字。"""
    return {"raw_merged_text": merged_text}


# 1. 請購單 
def extract_requisition_data(merged_text: str, tokens: list[dict]) -> dict:
    result: dict[str, Any] = {
        "doc_type":         "requisition",
        "applicant":        None,
        "requisition_date": None,
        "requisition_no":   None,
        "department":       None,
        "company_name":     None,
        "vendor_no":        None,
        "total_amount":     None,
        "items":            [],
    }

    #表頭欄位 
    result["applicant"]    = _token_value_after_key(tokens, ["申請人"])
    result["department"]   = _token_value_after_key(tokens, ["請購部門", "請購部门", "請購部"])
    result["requisition_no"] = _token_value_after_key(tokens, ["請購編號", "請購编号", "請購号", "請購編"])
    result["company_name"] = _token_value_after_key(tokens, ["公司名稱", "公司名称", "公司名"])
    result["vendor_no"]    = _token_value_after_key(tokens, ["廠商編號", "廠商编号", "廠商号", "廠商編", "廠商號"])

    # Regex 備援機制：如果空間搜尋失敗，從合併的字串中挽救
    if not result["department"]:
        result["department"] = _field_re(r"(?:請購部門|請購部)[\s：:]*([^\s]+)", merged_text)
    if not result["company_name"]:
        result["company_name"] = _field_re(r"(?:公司名稱|公司名)[\s：:]*([^\s]+)", merged_text)
    if not result["vendor_no"]:
        result["vendor_no"] = _field_re(r"(?:廠商編號|廠商号|廠商號)[\s：:]*([^\s]+)", merged_text)

    # 日期
    date_raw = _token_value_after_key(tokens, ["請購日期", "請日期", "購日期"])
    if date_raw:
        result["requisition_date"] = _parse_date(date_raw)
    if not result["requisition_date"]:
        seg = re.search(r"(?:請購日期|請日期)[\s：:]*(.{0,30})", merged_text)
        if seg:
            result["requisition_date"] = _parse_date(seg.group(1))

    #合計
    amt = re.search(r"(?:合計|總計|Total)[\s\n：:]*([\d,]+)", merged_text)
    if amt:
        result["total_amount"] = _parse_amount(amt.group(1))

    #明細 (Regex 解析合併行) 
    item_pat = re.compile(
        r"^(\d{1,4})\s+"                              # 項次 (必填)
        r"(\d{3,8})\s+"                               # 物料編號 (必填)
        r"(?:([^\d\s]+(?:[\s　][^\d\s]+)*)\s+)?"      # 品名 (可選，防漏印)
        r"([\d,]+(?:\.\d+)?)\s+"                       # 數量 (必填)
        r"([\d,]+(?:\.\d+)?)\s+"                       # 單價 (必填)
        r"([\d,]+(?:\.\d+)?)\s*$",                     # 金額 (必填)
        re.MULTILINE
    )
    
    for m in item_pat.finditer(merged_text):
        name = m.group(3).strip() if m.group(3) else "(未辨識品名)"
        if name in _SKIP_VALUES:
            continue
            
        result["items"].append({
            "item_no":     m.group(1),
            "material_no": m.group(2),
            "name":        name,
            "quantity":    _parse_amount(m.group(4)),
            "unit_price":  _parse_amount(m.group(5)),
            "amount":      _parse_amount(m.group(6)),
        })

    # 若 Regex 完全抓不到，啟用備用重建邏輯
    if not result["items"]:
        result["items"] = _rebuild_requisition_items(tokens)

    return result

def _rebuild_requisition_items(tokens: list[dict]) -> list[dict]:
    name_tokens = [
        t for t in tokens
        if re.search(r"[\u4e00-\u9fff]", t["text"])
        and t["text"] not in _SKIP_VALUES
        and len(t["text"]) >= 2
    ]

    items = []
    for nt in name_tokens:
        nearby_nums = [
            t for t in tokens
            if abs(t["y"] - nt["y"]) < 30
            and re.fullmatch(r"[\d,]+", t["text"])
        ]
        nearby_nums.sort(key=lambda t: t["x"])
        nums = [_parse_amount(t["text"]) for t in nearby_nums if _parse_amount(t["text"])]

        item_no_candidates = [
            t for t in tokens
            if abs(t["y"] - nt["y"]) < 30
            and re.fullmatch(r"\d{1,4}", t["text"])
        ]
        item_no = item_no_candidates[0]["text"] if item_no_candidates else None

        mat_candidates = [
            t for t in tokens
            if abs(t["y"] - nt["y"]) < 30
            and re.fullmatch(r"\d{3,6}", t["text"])
            and t != (item_no_candidates[0] if item_no_candidates else None)
        ]
        material_no = mat_candidates[0]["text"] if mat_candidates else None

        if len(nums) >= 3:
            nums_sorted = sorted(nums)
            quantity   = nums_sorted[0]
            unit_price = nums_sorted[1]
            amount     = nums_sorted[-1]
        elif len(nums) == 2:
            quantity = nums[0]
            amount   = nums[1]
            unit_price = None
        elif len(nums) == 1:
            amount = nums[0]
            quantity = unit_price = None
        else:
            quantity = unit_price = amount = None

        items.append({
            "item_no":     item_no,
            "material_no": material_no,
            "name":        nt["text"],
            "quantity":    quantity,
            "unit_price":  unit_price,
            "amount":      amount,
        })

    return items

# 2. 採購單 
def extract_po_data(merged_text: str, tokens: list[dict]) -> dict:
    result: dict[str, Any] = {
        "doc_type":       "purchase_order",
        "purchaser":      None,
        "department":     None,
        "requisition_no": None,
        "po_number":      None,
        "vendor_name":    None,
        "tax_id":         None,
        "vendor_contact": None,
        "vendor_phone":   None,
        "vendor_address": None,
        "delivery_date":  None,
        "payment_date":   None,
        "payment_method": None,
        "total_amount":   None,
        "items":          [],
    }

    #表頭欄位
    result["purchaser"]      = _token_value_after_key(tokens, ["採購人員", "採購人", "探購人員", "探購人"])
    result["department"]     = _token_value_after_key(tokens, ["採購部門", "採購部门", "採購部", "探購部門", "探購部"])
    result["requisition_no"] = _token_value_after_key(tokens, ["請購單號", "請購单号", "請購單", "請購單号"])
    result["po_number"]      = _token_value_after_key(tokens, ["採購單號", "採購单号", "採購單", "探購單号", "探購單號"])
    result["vendor_name"]    = _token_value_after_key(tokens, ["供應商名稱", "供應商名称", "供應商名"])
    result["payment_method"] = _token_value_after_key(tokens, ["付款方式"])
    result["vendor_contact"] = _token_value_after_key(tokens, ["供應商聯絡人", "聯絡人"])
    
    result["vendor_phone"]   = _token_value_after_key(tokens, ["供應商電話", "供應商电话", "電話"])
    result["vendor_address"] = _token_value_after_key(tokens, ["供應商地址", "地址"])

    # 統編 (加入「統一號」錯字支援)
    tax = _token_value_after_key(tokens, ["統一編號", "統編", "統一编号", "統一號"])
    if not tax:
        tax_match = re.search(r"(?:統一編號|統編|統一號)[\s：:]*([A-Za-z0-9]{4,10})", merged_text)
        tax = tax_match.group(1) if tax_match else None
    result["tax_id"] = tax

    # 日期雙保險
    for kw_list, date_key in [
        (["預計交貨日", "預計交貨", "交貨日", "計交貨日"], "delivery_date"), # 加入 "計交貨日" (預被吃掉)
        (["預計付款日", "預計付款", "付款日", "計付款日"], "payment_date"), # 加入 "計付款日" (預被吃掉)
    ]:
        date_raw = _token_value_after_key(tokens, kw_list)
        if date_raw:
            result[date_key] = _parse_date(date_raw)
        if not result[date_key]:
            seg = re.search(rf"(?:{'|'.join(kw_list)})[\s：:]*(.{{0,30}})", merged_text)
            if seg:
                result[date_key] = _parse_date(seg.group(1))

    # 合計 (加入「探購合計」錯字支援)
    amt_raw = _token_value_after_key(tokens, ["採購合計", "探購合計", "合計", "總計", "Total"])
    if amt_raw:
        result["total_amount"] = _parse_amount(amt_raw)
    if not result["total_amount"]:
        amt = re.search(r"(?:採購合計|探購合計|總計|合計|Total)[\s\n：:]*([\d,]+)", merged_text)
        if amt:
            result["total_amount"] = _parse_amount(amt.group(1))

    # 明細解析 (保持不變)
    item_pat = re.compile(
r"^(?:(\d{1,4})\s+)?"                          # 1. 項次
        r"(?:([^\d\s]+(?:[\s　][^\d\s]+)*)\s+)?"       # 2. 品名
        r"([\d,]+(?:\.\d+)?)\s+"                       # 3. 單價
        r"([\d,]+(?:\.\d+)?)\s+"                       # 4. 數量
        r"(?:([^\s\d]{1,10})\s+)?"                     # 5. 規格 / 單位 (如：份、個)
        r"([\d,]+(?:\.\d+)?)\s*$",                     # 6. 小計
        re.MULTILINE
    )
    
    for m in item_pat.finditer(merged_text):
        name = m.group(2).strip() if m.group(2) else "(未辨識品名)"
        if name in _SKIP_VALUES or re.fullmatch(r"[\d,\.]+", name):
            continue
            
        result["items"].append({
            "item_no":  m.group(1) or None,
            "name":     name,
            "unit_price": _parse_amount(m.group(3)),  # 取出單價
            "quantity": _parse_amount(m.group(4)),
            "unit":       m.group(5).strip() if m.group(5) else None, # 第 5 群組：單位
            "spec":       m.group(5).strip() if m.group(5) else None, # 同步存一份給規格
            "subtotal":   _parse_amount(m.group(6)),  # 第 6 群組：小計
        })

    if not result["items"]:
        result["items"] = _rebuild_po_items(tokens)

    return result

def _rebuild_po_items(tokens: list[dict]) -> list[dict]:
    """從散列 token 重建採購單明細行（項次、品名、數量、單位、小計）"""
    name_tokens = [
        t for t in tokens
        if re.search(r"[\u4e00-\u9fff]", t["text"])
        and t["text"] not in _SKIP_VALUES
        and len(t["text"]) >= 2
    ]
    items = []
    
    for nt in name_tokens:
        # 尋找同行 (y 誤差 < 30) 的其他文字
        nearby = [
            t for t in tokens
            if abs(t["y"] - nt["y"]) < 30 and t["text"] != nt["text"]
        ]
        nearby.sort(key=lambda t: t["x"])
        
        nums = [_parse_amount(t["text"]) for t in nearby
                if re.fullmatch(r"[\d,]+(?:\.\d+)?", t["text"]) and _parse_amount(t["text"])]
        
        specs = [t["text"] for t in nearby
                 if re.fullmatch(r"[\u4e00-\u9fff\w]{1,5}", t["text"])
                 and t["text"] not in _SKIP_VALUES]
        
        units = [t["text"] for t in nearby
                 if re.fullmatch(r"[\u4e00-\u9fff]{1,3}", t["text"])
                 and t["text"] not in _SKIP_VALUES]

        item_no_t = [t for t in nearby if re.fullmatch(r"\d{1,4}", t["text"])]
        item_no = item_no_t[0]["text"] if item_no_t else None

        # 採購單數字邏輯：通常較小的數字是數量，較大的是小計金額
        if len(nums) >= 3:
            nums_sorted = sorted(nums)
            quantity   = nums_sorted[0]
            unit_price = nums_sorted[1]
            subtotal   = nums_sorted[-1]
        elif len(nums) == 2:
            quantity   = min(nums)
            subtotal   = max(nums)
            unit_price = None
        else:
            quantity = unit_price = subtotal = None

        items.append({
            "item_no":  item_no,
            "name":     nt["text"],
            "unit_price": unit_price,
            "quantity": quantity,
            "spec":       specs[0] if specs else None,
            "subtotal": subtotal,
        })
        
    return items

# 3. 發票
def extract_invoice_data(merged_text: str, tokens: list[dict]) -> dict:
    result: dict[str, Any] = {
        "doc_type":       "invoice",
        "invoice_number": None,
        "tax_id":         None,
        "date":           None,
        "vendor_name":    None,
        "total_amount":   None,
        "items":          [],
    }

    # ── 表頭欄位 ──────────────────────────────
    
    # 1. 發票號碼：獨立 Token 全域掃描 (專解漂浮在空中的 XX012345678)
    inv_token = next((t["text"] for t in tokens if re.fullmatch(r"[A-Z]{2}[\s-]*\d{7,9}", t["text"])), None)
    if inv_token:
        result["invoice_number"] = inv_token.replace(" ", "").replace("-", "")
    else:
        inv = re.search(r"([A-Z]{2})[\s-]*(\d{7,9})", merged_text)
        if inv:
            result["invoice_number"] = f"{inv.group(1)}{inv.group(2)}"

    # 買受人 (客戶)
    result["vendor_name"] = _token_value_after_key(tokens, ["買受人", "買方", "客戶名稱"])
    if not result["vendor_name"]:
        vendor_re = re.search(r"(?:買受人|買方)[\s：:]*([^\s\n]+)", merged_text)
        result["vendor_name"] = vendor_re.group(1).strip() if vendor_re else None

    # 統編 
    tax = _token_value_after_key(tokens, ["統一編號", "統編", "統一编号", "統一號"])
    if not tax:
        tax_match = re.search(r"(?:統一編號|統編|買受人統編|統一號)[\s：:]*([A-Za-z0-9]{4,10})", merged_text)
        if tax_match:
            tax = tax_match.group(1)
        else:
            backup = re.search(r"(?<!\d)(\d{8})(?!\d)", merged_text)
            tax = backup.group(1) if backup else None
    result["tax_id"] = tax

    # 日期 
    date_raw = _token_value_after_key(tokens, ["日期", "開立日期", "中華民國"])
    if date_raw:
        result["date"] = _parse_date(date_raw)
    if not result["date"]:
        result["date"] = _parse_date(merged_text)

    # 總金額
    amt_raw = _token_value_after_key(tokens, ["總計", "合計", "總金額", "Total"])
    if amt_raw:
        result["total_amount"] = _parse_amount(amt_raw)
    if not result["total_amount"]:
        amt = re.search(r"(?:總計|總金額|合計|Total)[\s\n：:]*([\d,]+)", merged_text)
        if amt:
            result["total_amount"] = _parse_amount(amt.group(1))

    # ── 明細解析 (雙引擎競賽機制) ──────────────────────────────────
    regex_items = []
    
    # 1：三聯式發票表格格式
    item_pat_table = re.compile(
        r"^([^\d\s]+(?:[\s　][^\d\s]+){0,3})\s+"  
        r"([\d,]+(?:\.\d+)?)\s+"
        r"([\d,]+(?:\.\d+)?)\s+"
        r"([\d,]+(?:\.\d+)?)\s*$",
        re.MULTILINE
    )
    
    
    noise_keywords = ["地址", "品名", "單價", "金額", "數量", "偏", "合計", "總計", "免稅", "營業稅", "專用章", "發票", "營業人"]

    for m in item_pat_table.finditer(merged_text):
        name = m.group(1).strip()
        
        # 子字串比對防護
        if len(name) > 15 or any(noise in name for noise in noise_keywords):
            continue
        # 完全比對防護
        if name in _SKIP_VALUES or re.fullmatch(r"[\d,\.]+", name):
            continue
            
        regex_items.append({
            "name":       name,
            "quantity":   _parse_amount(m.group(2)),
            "unit_price": _parse_amount(m.group(3)),
            "amount":     _parse_amount(m.group(4)),
        })
        
    # 軌道 2：傳統超商電子發票格式
    if not regex_items:
        for m in re.finditer(r"([^\d×＠＝\n]+)\s*[×xX]\s*([\d,]+)", merged_text):
            name = m.group(1).strip()
            if name and name not in _SKIP_VALUES and len(name) <= 15:
                regex_items.append({
                    "name": name,
                    "quantity": _parse_amount(m.group(2)),
                })
                
    # 軌道 3：空間 Token 重建引擎
    token_items = _rebuild_invoice_items(tokens)

    # 🏆 智能決策：誰抓到的有效明細多，就用誰的
    if len(token_items) >= len(regex_items) and len(token_items) > 0:
        result["items"] = token_items
    else:
        result["items"] = regex_items

    return result

def _rebuild_invoice_items(tokens: list[dict]) -> list[dict]:
    """從散列 token 重建發票明細行（品名、數量、單價、金額）"""
    
    # 🚨 同步更新：嚴格過濾雜訊，封殺所有印章與標題字眼
    noise_keywords = ["地址", "品名", "單價", "金額", "數量", "偏", "合計", "總計", "免稅", "營業稅", "專用章", "發票", "營業人"]
    
    name_tokens = [
        t for t in tokens
        if re.search(r"[\u4e00-\u9fff]", t["text"])
        and t["text"] not in _SKIP_VALUES
        and len(t["text"]) >= 2
        and not any(noise in t["text"] for noise in noise_keywords)
    ]
    
    items = []
    for nt in name_tokens:
        nearby = [
            t for t in tokens
            if abs(t["y"] - nt["y"]) < 30 and t["text"] != nt["text"]
        ]
        nearby.sort(key=lambda t: t["x"])
        
        nums = [_parse_amount(t["text"]) for t in nearby
                if re.fullmatch(r"[\d,]+(?:\.\d+)?", t["text"]) and _parse_amount(t["text"])]
        
        if len(nums) == 0:
            continue # 右邊完全沒有數字的，通常是廢話，直接丟棄
            
        # 三聯式發票數字邏輯：[數量, 單價, 金額]
        if len(nums) >= 3:
            nums_sorted = sorted(nums)
            quantity   = nums_sorted[0]
            unit_price = nums_sorted[1]
            amount     = nums_sorted[-1]
        elif len(nums) == 2:
            quantity = min(nums)
            amount = max(nums)
            unit_price = None
        elif len(nums) == 1:
            quantity = None
            amount = nums[0]
            unit_price = None
        else:
            quantity = unit_price = amount = None

        items.append({
            "name":       nt["text"],
            "quantity":   quantity,
            "unit_price": unit_price,
            "amount":     amount,
        })
        
    return items
#驗收單
def extract_receipt_data(merged_text: str, tokens: list[dict]) -> dict:
    result: dict[str, Any] = {
        "doc_type":      "goods_receipt",
        "po_number":     None,
        "applicant":     None,
        "purchaser":     None,
        "delivery_date": None,
        "receiver":      None,
        "asset_type":    None,
        "receipt_date":  None,
        "total_qty":     None,
        "total_amount":  None,   # ✨ 修復：把 total_amount 加回字典裡
        "accepted_qty":  None,
        "items":         [],
    }

    # 表頭欄位 
    result["po_number"]  = _token_value_after_key(tokens, ["採購單號", "探購單號", "採購單号", "探購單号", "採購單"])
    result["applicant"]  = _token_value_after_key(tokens, ["採購申請人", "申請人", "探購申請人"])
    result["purchaser"]  = _token_value_after_key(tokens, ["採購人員", "採購人", "探購人員", "探購人"])
    result["receiver"]   = _token_value_after_key(tokens, ["驗收人", "验收人", "收人"]) 
    result["asset_type"] = _token_value_after_key(tokens, ["資產種類", "资产种类", "產種類"])

    # Regex 備援機制 
    if not result["po_number"]:
        result["po_number"] = _field_re(r"(?:採購單號|探購單號|採購單号|探購單号|採購單)[\s：:]*([A-Za-z0-9\-]+)", merged_text)
    if not result["applicant"]:
        result["applicant"] = _field_re(r"(?:採購申請人|申請人|探購申請人)[\s：:]*([^\s\n]+)", merged_text)
    if not result["receiver"]:
        recv = re.search(r"(?<!簽名)(?:驗收人|验收人|收人)[\s：:]*([^\s\n]+)", merged_text)
        if recv and "簽名" not in recv.group(1):
            result["receiver"] = recv.group(1).strip()
    if not result["asset_type"]:
        result["asset_type"] = _field_re(r"(?:資產種類|资产种类|產種類)[\s：:]*([^\s\n]+)", merged_text)

    # 日期 (雙軌機制)
    for kw_list, date_key in [
        (["到貨日期", "到货日期", "到貨日"], "delivery_date"),
        (["驗收日期", "验收日期", "驗收日", "收日期"], "receipt_date"),
    ]:
        date_raw = _token_value_after_key(tokens, kw_list)
        if date_raw:
            result[date_key] = _parse_date(date_raw)
        if not result[date_key]:
            seg = re.search(rf"(?:{'|'.join(kw_list)})[\s：:]*(.{{0,30}})", merged_text)
            if seg:
                result[date_key] = _parse_date(seg.group(1))

    # 合計件數 / 驗收合格數量 (total_qty) 繁簡體與錯字全面覆蓋 
    t_qty_keywords = [
        
        "驗收數量"
    ]
    t_qty = _token_value_after_key(tokens, t_qty_keywords)
    if t_qty:
        result["total_qty"] = _parse_amount(t_qty)
        
    if not result["total_qty"]:
        # ✨ 修復：在分隔符號中加入 \| 和 \- 等表格線干擾符號
        amt = re.search(rf"(?:{'|'.join(t_qty_keywords)})[\s\n：:\|\-]*([\d,]+)", merged_text)
        if amt:
            result["total_qty"] = _parse_amount(amt.group(1))
    
    # 合格數量 (accepted_qty) 
    a_qty_keywords = [
        "驗收合格數量", "验收合格数量", "驗收合格数量", "验收合格", 
        "合格數量", "合格数量"
    ]
    a_qty = _token_value_after_key(tokens, a_qty_keywords)
    if a_qty:
        result["accepted_qty"] = _parse_amount(a_qty)
        
    if not result["accepted_qty"]:
        amt_a = re.search(rf"(?:{'|'.join(a_qty_keywords)})[\s\n：:\|\-]*([\d,]+)", merged_text)
        if amt_a:
            result["accepted_qty"] = _parse_amount(amt_a.group(1))

    # 合計金額 (total_amount) 
    t_amt = _token_value_after_key(tokens, ["合計", "總計"])
    if t_amt and _parse_amount(t_amt):
        if _parse_amount(t_amt) > 100: 
            result["total_amount"] = _parse_amount(t_amt)
            
    if not result["total_amount"]:
        # ✨ 防呆更新：同步加入表格線干擾符號 \|
        amt_match = re.search(r"(?<!件數)(?<!數量)(?<!数量)(?:合計|總計)[\s\n：:\|\-]*([\d,]+)", merged_text)
        if amt_match:
            result["total_amount"] = _parse_amount(amt_match.group(1))
    # 明細解析 (Regex 優先) 
    item_pat = re.compile(
        r"^(\d{1,4})\s+"                             # 項次
        r"([^\d\s]+(?:[\s　][^\d\s]+)*)\s+"          # 品名
        r"([\d,]+(?:\.\d+)?)\s+"                     # 數量/收貨數量
        r"([\d,]+(?:\.\d+)?)\s*$",                   # 金額
        re.MULTILINE
    )
    
    for m in item_pat.finditer(merged_text):
        name = m.group(2).strip()
        if name in _SKIP_VALUES:
            continue
        result["items"].append({
            "item_no":  m.group(1),
            "name":     name,
            "quantity": _parse_amount(m.group(3)),
            "amount":   _parse_amount(m.group(4)),
        })

    #  明細解析 (Token 重建備援) 
    if not result["items"]:
        # ✨ 加入收貨數量、驗收合格數量等新雜訊
        noise_kws = ["備註", "項次", "品名", "數量", "数量", "收貨數量", "收货数量", 
            "合計件數", "驗收合格數量", "验收合格数量", "合格數量", "合格数量", 
            "驗收人簽名", "驗收日期", "簽名", "收人", "收日期", "金額", "金额", "合計", "总计"
            ]
        name_tokens = [
            t for t in tokens
            if re.search(r"[\u4e00-\u9fff]", t["text"])
            and t["text"] not in _SKIP_VALUES
            and len(t["text"]) >= 2
            and not any(n in t["text"] for n in noise_kws)
        ]
        
        for nt in name_tokens:
            nearby = [t for t in tokens if abs(t["y"] - nt["y"]) < 30 and t["text"] != nt["text"]]
            nearby.sort(key=lambda t: t["x"])
            
            nums = [_parse_amount(t["text"]) for t in nearby if re.fullmatch(r"[\d,]+(?:\\.\\d+)?", t["text"])]
            item_no_t = [t for t in nearby if re.fullmatch(r"\d{1,4}", t["text"])]
            
            if nums:
                result["items"].append({
                    "item_no": item_no_t[0]["text"] if item_no_t else None,
                    "name":    nt["text"],
                    "quantity": min(nums) if len(nums) >= 2 else nums[0],
                    "amount":   max(nums) if len(nums) >= 2 else None
                })


    #  備援：OCR 漏掃合格數量時，由明細加總推算 
    if not result["total_qty"] and result["items"]:
        qty_sum = sum(
            item["quantity"] for item in result["items"]
            if isinstance(item.get("quantity"), (int, float))
        )
        if qty_sum > 0:
            result["total_qty"] = qty_sum
    return result