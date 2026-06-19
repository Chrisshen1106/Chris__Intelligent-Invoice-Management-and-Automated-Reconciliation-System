import { http, HttpResponse } from 'msw';
import invoicesPendingGet from './finance/invoicesPending_get.json';
import invoicesInvoiceNoGet from './finance/invoicesInvoiceNo_get.json';
import invoicesApprovePost from './finance/invoicesApprove_post.json';
import invoicesRejectPost from './finance/invoicesReject_post.json';
import invoicesHoldPost from './finance/invoicesHold_post.json';
import logsGet from './finance/logs_get.json';

const API_BASE = '/api/finance';

const pendingPurchaseOrders = [
  {
    poId: 'po-9901',
    poNo: 'PO-9901',
    purchaser: '王小明',
    department: '資訊部',
    vendorName: '測試供應商',
    poDate: '2026-05-20',
    totalAmount: 120000,
    submittedAt: '2026-05-20 09:30:00',
  },
];

const matchGroupsPending = [
  {
    poNo: 'PO-8801',
    vendorName: '宏遠科技',
    poDate: '2026-03-20',
    invoiceNo: 'INV-2026-001',
    invoiceDate: '2026-03-21',
    grNo: 'GR-2026-001',
    totalAmount: 625000,
    groupStatus: 'pending',
  },
  {
    poNo: 'PO-8802',
    vendorName: '全聯資訊',
    poDate: '2026-03-22',
    invoiceNo: null,
    invoiceDate: null,
    grNo: 'GR-2026-002',
    totalAmount: 66500,
    groupStatus: 'pending',
  },
  {
    poNo: 'PO-8803',
    vendorName: '青山文具',
    poDate: '2026-03-23',
    invoiceNo: 'INV-2026-003',
    invoiceDate: '2026-03-24',
    grNo: 'GR-2026-003',
    totalAmount: 40800,
    groupStatus: 'onHold',
  },
];

const poReviewGroups = matchGroupsPending.map(row => ({
  poNo: row.poNo,
  vendorName: row.vendorName,
  poDate: row.poDate,
  totalAmount: row.totalAmount,
  groupStatus: row.groupStatus === 'pending' && row.invoiceNo && row.grNo ? 'complete' : row.groupStatus,
  missingDocuments: [
    ...(!row.grNo ? ['goodsReceipt'] : []),
    ...(!row.invoiceNo ? ['invoice'] : []),
  ],
  readyForMatch: Boolean(row.invoiceNo && row.grNo),
  priority: row.invoiceNo && row.grNo ? 10 : 1,
  purchaseOrder: { poNo: row.poNo, vendorName: row.vendorName, poDate: row.poDate, totalAmount: row.totalAmount },
  goodsReceipt: row.grNo ? { grNo: row.grNo } : null,
  invoice: row.invoiceNo ? { invoiceNo: row.invoiceNo, invoiceDate: row.invoiceDate, totalAmount: row.totalAmount } : null,
}));

const documentHistory = [
  {
    docId: 'po-8801',
    docType: 'purchaseOrder',
    docNo: 'PO-8801',
    submittedAt: '2026-03-20 09:10:00',
    updatedAt: '2026-03-20 10:20:00',
    totalAmount: 625000,
    status: 'approved',
    vendorName: 'Mock Vendor',
    employeeName: 'Mock Employee',
    uploadedBy: 'Mock Employee',
  },
  {
    docId: 'inv-8801',
    docType: 'invoice',
    docNo: 'INV-2026-001',
    submittedAt: '2026-03-21 13:10:00',
    updatedAt: '2026-03-21 13:10:00',
    totalAmount: 625000,
    status: 'pendingMatch',
    vendorName: 'Mock Vendor',
    employeeName: 'Mock Employee',
    uploadedBy: 'Mock Employee',
  },
];

const employeeOperationRecords = [
  {
    recordType: 'upload',
    docType: 'purchaseOrder',
    docId: 'po-8801',
    docNo: 'PO-8801',
    actionType: 'submit',
    actedAt: '2026-03-20 09:10:00',
    actorName: 'Mock Employee',
    actorEmail: 'employee@example.com',
    actorRoleCode: 'E',
    status: 'pending',
    comment: 'Submitted purchase order',
  },
];

const matchGroupDetails = {
  'PO-8801': {
    poNo: 'PO-8801',
    vendorName: '宏遠科技',
    groupStatus: 'pending',
    po: {
      poId: 'po-8801',
      purchaser: '王小明',
      department: '資訊部',
      taxId: '12345678',
      poDate: '2026-03-20',
      totalAmount: 625000,
      uploadedBy: '王小明',
      items: [
        { lineNo: 1, itemName: 'MacBook Pro', quantity: 10, unitPrice: 60000, lineAmount: 600000 },
        { lineNo: 2, itemName: 'Magic Mouse', quantity: 10, unitPrice: 2500, lineAmount: 25000 },
      ],
    },
    gr: {
      grId: 'gr-8801',
      grNo: 'GR-2026-001',
      applicant: '王小明',
      receiver: '陳怡君',
      grDate: '2026-03-21',
      totalQty: 20,
      totalAmount: 625000,
      uploadedBy: '陳怡君',
      items: [
        { lineNo: 1, itemName: 'MacBook Pro', receivedQty: 10, acceptedQty: 10, lineAmount: 600000 },
        { lineNo: 2, itemName: 'Magic Mouse', receivedQty: 10, acceptedQty: 10, lineAmount: 25000 },
      ],
    },
    invoice: {
      invoiceId: 'inv-8801',
      invoiceNo: 'INV-2026-001',
      invoiceDate: '2026-03-21',
      totalAmount: 625000,
      uploadedBy: '林志豪',
      items: [
        { lineNo: 1, itemName: 'MacBook Pro', quantity: 10, unitPrice: 60000 },
        { lineNo: 2, itemName: 'Magic Mouse', quantity: 10, unitPrice: 2500 },
      ],
    },
    comparisonItems: [
      { itemName: 'MacBook Pro', poQty: 10, poUnitPrice: 60000, grQty: 10, grUnitPrice: 60000, invoiceQty: 10, invoiceUnitPrice: 60000 },
      { itemName: 'Magic Mouse', poQty: 10, poUnitPrice: 2500, grQty: 10, grUnitPrice: 2500, invoiceQty: 10, invoiceUnitPrice: 2500 },
    ],
  },
  'PO-8803': {
    poNo: 'PO-8803',
    vendorName: '青山文具',
    groupStatus: 'onHold',
    po: {
      poId: 'po-8803',
      purchaser: '黃雅婷',
      department: '行政部',
      taxId: '87654321',
      poDate: '2026-03-23',
      totalAmount: 28500,
      uploadedBy: '黃雅婷',
      items: [
        { lineNo: 1, itemName: 'A4 影印紙', quantity: 30, unitPrice: 800, lineAmount: 24000 },
        { lineNo: 2, itemName: '訂書機', quantity: 10, unitPrice: 450, lineAmount: 4500 },
      ],
    },
    gr: {
      grId: 'gr-8803',
      grNo: 'GR-2026-003',
      applicant: '黃雅婷',
      receiver: '張凱翔',
      grDate: '2026-03-24',
      totalQty: 40,
      totalAmount: 28500,
      uploadedBy: '張凱翔',
      items: [
        { lineNo: 1, itemName: 'A4 影印紙', receivedQty: 30, acceptedQty: 30, lineAmount: 24000 },
        { lineNo: 2, itemName: '訂書機', receivedQty: 10, acceptedQty: 10, lineAmount: 4500 },
      ],
    },
    invoice: {
      invoiceId: 'inv-8803',
      invoiceNo: 'INV-2026-003',
      invoiceDate: '2026-03-24',
      totalAmount: 40800,
      uploadedBy: '黃雅婷',
      items: [
        { lineNo: 1, itemName: 'A4 影印紙', quantity: 33, unitPrice: 1100 },
        { lineNo: 2, itemName: '訂書機', quantity: 10, unitPrice: 450 },
      ],
    },
    comparisonItems: [
      { itemName: 'A4 影印紙', poQty: 30, poUnitPrice: 800, grQty: 30, grUnitPrice: 800, invoiceQty: 33, invoiceUnitPrice: 1100 },
      { itemName: '訂書機', poQty: 10, poUnitPrice: 450, grQty: 10, grUnitPrice: 450, invoiceQty: 10, invoiceUnitPrice: 450 },
    ],
  },
};

export const financeHandlers = [
  http.get(`${API_BASE}/purchase-orders/pending`, () => {
    return HttpResponse.json(pendingPurchaseOrders);
  }),
  http.post(`${API_BASE}/purchase-orders/:poNo/review`, async ({ params, request }) => {
    const body = await request.json().catch(() => ({}));
    const rejected = body.actionType === 2;
    return HttpResponse.json({
      success: true,
      poNo: params.poNo,
      status: rejected ? 'rejected' : 'approved',
      message: 'Purchase order reviewed successfully',
    });
  }),
  http.get(`${API_BASE}/match-groups/pending`, () => {
    return HttpResponse.json(matchGroupsPending);
  }),
  http.get(`${API_BASE}/po-review-groups`, () => {
    return HttpResponse.json(poReviewGroups);
  }),
  http.get(`${API_BASE}/match-groups/:poNo`, ({ params }) => {
    return HttpResponse.json(matchGroupDetails[params.poNo] || matchGroupDetails['PO-8801']);
  }),
  http.post(`${API_BASE}/match-groups/:poNo/approve`, ({ params }) => {
    return HttpResponse.json({ success: true, poNo: params.poNo, message: 'Match group approved successfully' });
  }),
  http.post(`${API_BASE}/match-groups/:poNo/reject`, ({ params }) => {
    return HttpResponse.json({ success: true, poNo: params.poNo, groupStatus: 'onHold' });
  }),
  http.post(`${API_BASE}/match-groups/:poNo/hold`, ({ params }) => {
    return HttpResponse.json({ success: true, poNo: params.poNo, groupStatus: 'onHold' });
  }),
  http.post(`${API_BASE}/match-groups/:poNo/void`, ({ params }) => {
    return HttpResponse.json({ success: true, poNo: params.poNo, groupStatus: 'void', message: 'Match group voided successfully' });
  }),
  http.get(`${API_BASE}/invoices/pending`, () => {
    return HttpResponse.json(invoicesPendingGet);
  }),
  http.get(`${API_BASE}/invoices/:invoiceNo`, () => {
    return HttpResponse.json(invoicesInvoiceNoGet);
  }),
  http.post(`${API_BASE}/invoices/approve`, () => {
    return HttpResponse.json(invoicesApprovePost);
  }),
  http.post(`${API_BASE}/invoices/:invoiceNo/reject`, () => {
    return HttpResponse.json(invoicesRejectPost);
  }),
  http.post(`${API_BASE}/invoices/:invoiceNo/hold`, () => {
    return HttpResponse.json(invoicesHoldPost);
  }),
  http.get(`${API_BASE}/logs`, () => {
    return HttpResponse.json(logsGet);
  }),
  http.get(`${API_BASE}/document-history`, () => {
    return HttpResponse.json(documentHistory);
  }),
  http.get(`${API_BASE}/employee-operation-records`, () => {
    return HttpResponse.json(employeeOperationRecords);
  })
];

export default financeHandlers;
