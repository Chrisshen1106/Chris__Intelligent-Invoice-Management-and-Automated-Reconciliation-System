import { http, HttpResponse } from 'msw';
import claimsGet from './manager/claims_get.json';
import claimDetailGet from './manager/claimDetail_get.json';
import reconciliationsExportPost from './manager/reconciliationsExport_post.json';

const API_BASE = '/api/manager';
const sampleMatchGroup = {
  groupId: 'MG-202604-001',
  poNo: 'PO-202604-001',
  purchaseNo: 'PO-202604-001',
  grNo: 'GR-202604-001',
  invoiceNo: 'JayChou_Invoice001',
  applicantName: 'Test Employee',
  applicantEmail: 'employee@example.com',
  vendorName: '杰威爾音樂有限公司',
  applyDate: '2026-04-01',
  amount: 2000,
  groupStatus: 'pending',
  statusDescription: '待核准',
  purchaseOrder: {
    poNo: 'PO-202604-001',
    totalAmount: 2000,
    vendorName: '杰威爾音樂有限公司',
    status: 'approved'
  },
  goodsReceipt: {
    grNo: 'GR-202604-001',
    receivedDate: '2026-04-01',
    status: 'received'
  },
  invoice: claimDetailGet.invoice,
  comparisonItems: claimDetailGet.invoice.items
};

export const managerHandlers = [
  http.get(`${API_BASE}/match-groups`, () => {
    return HttpResponse.json([sampleMatchGroup]);
  }),
  http.get(`${API_BASE}/match-groups/:poNo`, ({ params }) => {
    return HttpResponse.json({
      group: {
        ...sampleMatchGroup,
        poNo: params.poNo || sampleMatchGroup.poNo,
        purchaseNo: params.poNo || sampleMatchGroup.purchaseNo
      },
      detail: {
        purchaseOrder: sampleMatchGroup.purchaseOrder,
        goodsReceipt: sampleMatchGroup.goodsReceipt,
        invoice: sampleMatchGroup.invoice
      }
    });
  }),
  http.get(`${API_BASE}/match-groups/:poNo/files/:docType`, ({ params }) => {
    const fileMap = {
      purchaseOrder: '/invoices/sample_purchase_order.png',
      goodsReceipt: '/invoices/sample_goods_receipt.png',
      invoice: '/invoices/sample_invoice.png'
    };
    const target = fileMap[params.docType];
    if (!target) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.redirect(target);
  }),
  http.get(`${API_BASE}/claims`, () => {
    return HttpResponse.json(claimsGet);
  }),
  http.get(`${API_BASE}/claims/:claimId`, () => {
    return HttpResponse.json(claimDetailGet);
  }),
  http.post(`${API_BASE}/reconciliations/export`, () => {
    return HttpResponse.json(reconciliationsExportPost);
  })
];

export default managerHandlers;
