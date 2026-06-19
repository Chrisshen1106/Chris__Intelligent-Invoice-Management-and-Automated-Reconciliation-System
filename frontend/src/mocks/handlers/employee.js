import { http, HttpResponse } from 'msw';
import purchaseOrdersPost from './employee/purchaseOrders_post.json';
import goodsReceiptsPost from './employee/goodsReceipts_post.json';
import invoicesOcrPost from './employee/invoicesOcr_post.json';
import purchaseOrdersOcrPost from './employee/purchaseOrdersOcr_post.json';
import goodsReceiptsOcrPost from './employee/goodsReceiptsOcr_post.json';
import invoicesPost from './employee/invoices_post.json';
import invoicesRejectedGet from './employee/invoicesRejected_get.json';
import invoicesInvoiceNoPut from './employee/invoicesInvoiceNo_put.json';
import purchaseOrdersApprovedGet from './employee/purchaseOrdersApproved_get.json';
import documentsGet from './employee/documents_get.json';
import documentsDocIdInvoiceGet from './employee/documentsDocIdInvoice_get.json';
import documentsDocIdPoGet from './employee/documentsDocIdPo_get.json';
import documentsDocIdGrGet from './employee/documentsDocIdGr_get.json';

const API_BASE = '/api/employee';

export const employeeHandlers = [
  // --- OCR 辨識端點 ---
  http.post(`${API_BASE}/purchase-orders/ocr`, () => {
    return HttpResponse.json(purchaseOrdersOcrPost);
  }),
  http.post(`${API_BASE}/goods-receipts/ocr`, () => {
    return HttpResponse.json(goodsReceiptsOcrPost);
  }),
  http.post(`${API_BASE}/invoices/ocr`, () => {
    return HttpResponse.json(invoicesOcrPost);
  }),

  // --- 送出端點 ---
  // 建立採購單 (含 taxId, items)
  http.post(`${API_BASE}/purchase-orders`, async ({ request }) => {
    const formData = await request.formData();
    const rawPoData = formData.get('poData');

    let parsedPoData = {};
    if (typeof rawPoData === 'string') {
      try { parsedPoData = JSON.parse(rawPoData); } catch { /* ignore */ }
    }

    console.log('[MSW] POST /purchase-orders', {
      poNo: parsedPoData.poNo,
      taxId: parsedPoData.taxId,
      itemsCount: parsedPoData.items?.length || 0,
    });

    return HttpResponse.json({
      ...purchaseOrdersPost,
      poNo: parsedPoData.poNo || purchaseOrdersPost.poNo,
    });
  }),

  // 建立驗收單 (含 items)
  http.post(`${API_BASE}/goods-receipts`, async ({ request }) => {
    const formData = await request.formData();
    const rawGrData = formData.get('grData');

    let parsedGrData = {};
    if (typeof rawGrData === 'string') {
      try { parsedGrData = JSON.parse(rawGrData); } catch { /* ignore */ }
    }

    console.log('[MSW] POST /goods-receipts', {
      grNo: parsedGrData.grNo,
      itemsCount: parsedGrData.items?.length || 0,
    });

    return HttpResponse.json({
      ...goodsReceiptsPost,
      grNo: parsedGrData.grNo || goodsReceiptsPost.grNo,
    });
  }),

  // 確認並送出發票
  http.post(`${API_BASE}/invoices`, async ({ request }) => {
    const formData = await request.formData();
    const rawInvoiceData = formData.get('invoiceData');

    let parsedInvoiceData = {};
    if (typeof rawInvoiceData === 'string') {
      try {
        parsedInvoiceData = JSON.parse(rawInvoiceData);
      } catch {
        parsedInvoiceData = {};
      }
    }

    return HttpResponse.json({
      ...invoicesPost,
      invoiceNo: parsedInvoiceData.invoiceNo || invoicesPost.invoiceNo,
    });
  }),

  // 取得合法採購單號清單
  http.get(`${API_BASE}/purchase-orders/approved`, () => {
    return HttpResponse.json(purchaseOrdersApprovedGet);
  }),

  // 取得已送出紀錄清單
  http.get(`${API_BASE}/documents`, () => {
    return HttpResponse.json(documentsGet);
  }),

  // 取得單筆紀錄詳細
  http.get(`${API_BASE}/documents/:docId`, ({ params }) => {
    const detailMap = {
      'DOC-001': documentsDocIdPoGet,
      'DOC-002': documentsDocIdGrGet,
      'DOC-003': documentsDocIdInvoiceGet,
    };
    const fallback = documentsDocIdInvoiceGet;
    const detail = detailMap[params.docId] || fallback;
    return HttpResponse.json({
      ...detail,
      docId: params.docId || detail.docId,
    });
  }),

  // 取得單據附件檔案 (僅提供預覽用資料)
  http.get(`${API_BASE}/documents/:docId/file`, () => {
    // 建立一個最小化的有效 PDF 結構
    const pdfString = `%PDF-1.4
1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj
2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj
3 0 obj <</Type /Page /Parent 2 0 R /Resources <</Font <</F1 4 0 R>>>> /MediaBox [0 0 300 200] /Contents 5 0 R>> endobj
4 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj
5 0 obj <</Length 44>> stream
BT
/F1 16 Tf
20 150 Td
(Mock PDF File) Tj
ET
endstream endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000056 00000 n 
0000000111 00000 n 
0000000236 00000 n 
0000000314 00000 n 
trailer <</Size 6 /Root 1 0 R>>
startxref
409
%%EOF`;

    // 轉換為 ArrayBuffer 二進位格式，避免前端出現無法載入 PDF 的錯誤
    const buffer = new TextEncoder().encode(pdfString).buffer;

    return new HttpResponse(buffer, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Length': buffer.byteLength.toString(),
      },
    });
  }),

  // 取得被退回的單據清單
  http.get(`${API_BASE}/documents/rejected`, () => {
    return HttpResponse.json(invoicesRejectedGet);
  }),

  // 重新編輯並送出退回發票
  http.put(`${API_BASE}/invoices/:invoiceNo`, ({ params }) => {
    return HttpResponse.json({
      ...invoicesInvoiceNoPut,
      invoiceNo: params.invoiceNo || invoicesInvoiceNoPut.invoiceNo,
    });
  })
];

export default employeeHandlers;
