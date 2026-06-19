"""
生成 4 種單據的假資料圖片，供前端 OCR 測試使用。
用法: python3 generate_samples.py
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# 嘗試載入系統中文字型
FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",                      # macOS
    "/System/Library/Fonts/STHeiti Medium.ttc",                 # macOS fallback
    "/System/Library/Fonts/Hiragino Sans GB.ttc",               # macOS fallback
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Linux
    "C:/Windows/Fonts/msjh.ttc",                                # Windows
]

def load_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

FONT_TITLE = load_font(28)
FONT_HEADER = load_font(20)
FONT_BODY = load_font(16)
FONT_SMALL = load_font(14)


def draw_table(draw, x, y, headers, rows, col_widths, font=None):
    """畫一個簡易文字表格"""
    if font is None:
        font = FONT_BODY
    row_h = 30
    # header
    cx = x
    for i, h in enumerate(headers):
        draw.text((cx + 5, y + 5), h, fill="black", font=FONT_SMALL)
        cx += col_widths[i]
    y += row_h
    draw.line([(x, y), (cx, y)], fill="black", width=1)
    # rows
    for row in rows:
        cx = x
        for i, val in enumerate(row):
            draw.text((cx + 5, y + 5), str(val), fill="black", font=font)
            cx += col_widths[i]
        y += row_h
    return y


def gen_invoice():
    """三聯式發票"""
    img = Image.new("RGB", (800, 650), "white")
    d = ImageDraw.Draw(img)

    # 標題
    d.text((250, 30), "三 聯 式 統 一 發 票", fill="black", font=FONT_TITLE)
    d.text((300, 70), "收 執 聯", fill="gray", font=FONT_HEADER)

    # 欄位
    y = 120
    fields = [
        ("發票號碼", "AA-12345678"),
        ("採購單號", "PO-20260405-001"),
        ("日期", "2026年04月08日"),
        ("供應商名稱", "大同文具供應商"),
        ("統一編號", "12345678"),
    ]
    for label, val in fields:
        d.text((60, y), f"{label}：", fill="black", font=FONT_BODY)
        d.text((220, y), val, fill="black", font=FONT_BODY)
        y += 35

    # 明細
    y += 10
    d.line([(50, y), (750, y)], fill="black", width=1)
    y += 5
    headers = ["品名", "數量", "單價", "金額"]
    col_w = [250, 120, 120, 120]
    rows = [
        ["A4 影印紙", "50", "100", "5,000"],
        ["碳粉匣",   "5",  "2,000", "10,000"],
    ]
    y = draw_table(d, 60, y, headers, rows, col_w)

    # 合計
    y += 15
    d.line([(50, y), (750, y)], fill="black", width=1)
    y += 10
    d.text((60, y), "合計", fill="black", font=FONT_HEADER)
    d.text((500, y), "15,000", fill="black", font=FONT_HEADER)

    path = os.path.join(OUTPUT_DIR, "sample_invoice.png")
    img.save(path)
    print(f"✅ 發票圖片已產生: {path}")


def gen_requisition():
    """請購單"""
    img = Image.new("RGB", (800, 720), "white")
    d = ImageDraw.Draw(img)

    d.text((300, 30), "請 購 單", fill="black", font=FONT_TITLE)

    y = 90
    fields = [
        ("申請人", "王小明"),
        ("請購日期", "2026年04月01日"),
        ("請購編號", "PR-20260401-001"),
        ("請購部門", "資訊部"),
        ("公司名稱", "台灣科技股份有限公司"),
        ("廠商編號", "V-0012"),
    ]
    for label, val in fields:
        d.text((60, y), f"{label}：", fill="black", font=FONT_BODY)
        d.text((220, y), val, fill="black", font=FONT_BODY)
        y += 35

    y += 10
    d.line([(50, y), (750, y)], fill="black", width=1)
    y += 5
    headers = ["項次", "物料編號", "品名", "數量", "單價", "金額"]
    col_w = [60, 100, 180, 80, 100, 100]
    rows = [
        ["1", "MAT-001", "A4 影印紙", "50", "100", "5,000"],
        ["2", "MAT-002", "碳粉匣",   "5",  "2,000", "10,000"],
    ]
    y = draw_table(d, 60, y, headers, rows, col_w, FONT_SMALL)

    y += 15
    d.line([(50, y), (750, y)], fill="black", width=1)
    y += 10
    d.text((60, y), "合計", fill="black", font=FONT_HEADER)
    d.text((500, y), "15,000", fill="black", font=FONT_HEADER)

    path = os.path.join(OUTPUT_DIR, "sample_requisition.png")
    img.save(path)
    print(f"✅ 請購單圖片已產生: {path}")


def gen_purchase_order():
    """採購單"""
    img = Image.new("RGB", (800, 780), "white")
    d = ImageDraw.Draw(img)

    d.text((300, 30), "採 購 單", fill="black", font=FONT_TITLE)

    y = 90
    fields = [
        ("採購人員", "李大華"),
        ("採購部門", "採購部"),
        ("請購單號", "PR-20260401-001"),
        ("採購單號", "PO-20260405-001"),
        ("供應商名稱", "大同文具供應商"),
        ("統一編號", "12345678"),
        ("預計交貨日", "2026年04月20日"),
        ("付款方式", "月結30天"),
    ]
    for label, val in fields:
        d.text((60, y), f"{label}：", fill="black", font=FONT_BODY)
        d.text((220, y), val, fill="black", font=FONT_BODY)
        y += 35

    y += 10
    d.line([(50, y), (750, y)], fill="black", width=1)
    y += 5
    headers = ["項次", "品名", "規格", "數量", "單位", "單價", "小計"]
    col_w = [50, 140, 100, 70, 60, 90, 100]
    rows = [
        ["1", "A4 影印紙", "",       "50", "包", "100",   "5,000"],
        ["2", "碳粉匣",   "HP 205A", "5",  "個", "2,000", "10,000"],
    ]
    y = draw_table(d, 60, y, headers, rows, col_w, FONT_SMALL)

    y += 15
    d.line([(50, y), (750, y)], fill="black", width=1)
    y += 10
    d.text((60, y), "採購合計", fill="black", font=FONT_HEADER)
    d.text((500, y), "15,000", fill="black", font=FONT_HEADER)

    path = os.path.join(OUTPUT_DIR, "sample_purchase_order.png")
    img.save(path)
    print(f"✅ 採購單圖片已產生: {path}")


def gen_goods_receipt():
    """驗收單"""
    img = Image.new("RGB", (800, 700), "white")
    d = ImageDraw.Draw(img)

    d.text((300, 30), "驗 收 單", fill="black", font=FONT_TITLE)

    y = 90
    fields = [
        ("採購單號", "PO-20260405-001"),
        ("採購申請人", "王小明"),
        ("驗收人", "張志偉"),
        ("驗收日期", "2026年04月10日"),
        ("合計件數", "55"),
    ]
    for label, val in fields:
        d.text((60, y), f"{label}：", fill="black", font=FONT_BODY)
        d.text((220, y), val, fill="black", font=FONT_BODY)
        y += 35

    y += 10
    d.line([(50, y), (750, y)], fill="black", width=1)
    y += 5
    headers = ["項次", "品名", "收貨數量", "驗收合格數量", "金額"]
    col_w = [60, 180, 110, 130, 120]
    rows = [
        ["1", "A4 影印紙", "50", "50", "5,000"],
        ["2", "碳粉匣",   "5",  "5",  "10,000"],
    ]
    y = draw_table(d, 60, y, headers, rows, col_w, FONT_SMALL)

    y += 15
    d.line([(50, y), (750, y)], fill="black", width=1)
    y += 10
    d.text((60, y), "合計", fill="black", font=FONT_HEADER)
    d.text((500, y), "15,000", fill="black", font=FONT_HEADER)

    path = os.path.join(OUTPUT_DIR, "sample_goods_receipt.png")
    img.save(path)
    print(f"✅ 驗收單圖片已產生: {path}")


if __name__ == "__main__":
    gen_invoice()
    gen_requisition()
    gen_purchase_order()
    gen_goods_receipt()
    print("\n🎉 全部完成！圖片在:", OUTPUT_DIR)
