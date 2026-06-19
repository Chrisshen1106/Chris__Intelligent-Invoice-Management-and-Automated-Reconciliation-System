<template>
  <div class="finance-page">
    <section v-if="!activePoNo" class="review-shell">
      <div class="top-tabs" role="tablist" :aria-label="t('finance.match.views_aria')">
        <button :class="['tab-btn', activeTab === 'poReview' ? 'tab-active' : '']" @click="switchTab('poReview')">
          {{ t('finance.match.po_review') }}
        </button>
        <button :class="['tab-btn', activeTab === 'review' ? 'tab-active' : '']" @click="switchTab('review')">
          {{ t('finance.match.review_list') }}
        </button>
        <button :class="['tab-btn', activeTab === 'history' ? 'tab-active' : '']" @click="switchTab('history')">
          {{ t('finance.match.history') }}
        </button>
        <button :class="['tab-btn', activeTab === 'operations' ? 'tab-active' : '']" @click="switchTab('operations')">
          {{ t('finance.match.employee_operations') }}
        </button>
      </div>

      <div v-if="activeTab === 'poReview'">
        <header class="page-header">
          <div>
            <h1>{{ t('finance.match.po_review_title') }}</h1>
            <p>{{ t('finance.match.po_review_subtitle') }}</p>
          </div>
          <button class="secondary-btn" @click="loadPendingPurchaseOrders" :disabled="loadingPoList">
            {{ loadingPoList ? t('finance.match.loading') : t('finance.match.refresh') }}
          </button>
        </header>

        <div v-if="poListError" class="empty-box error">{{ poListError }}</div>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('finance.match.po_no') }}</th>
                <th>{{ t('finance.match.vendor') }}</th>
                <th>{{ t('finance.match.purchaser') }}</th>
                <th>{{ t('finance.match.po_date') }}</th>
                <th>{{ t('finance.match.amount') }}</th>
                <th>{{ t('finance.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="po in pendingPurchaseOrders" :key="po.poNo || po.poId">
                <td class="key-cell">{{ po.poNo || '-' }}</td>
                <td>{{ po.vendorName || '-' }}</td>
                <td>{{ po.purchaser || '-' }}</td>
                <td>{{ po.poDate || '-' }}</td>
                <td>{{ formatCurrency(po.totalAmount) }}</td>
                <td>
                  <div class="row-actions">
                    <button class="secondary-btn sm" :disabled="decisionBusy || !po.poNo" @click="openPurchaseOrderPreview(po.poNo)">
                      {{ t('finance.match.preview') }}
                    </button>
                    <button class="approve-btn sm" :disabled="decisionBusy || !po.poNo" @click="approvePurchaseOrder(po.poNo)">
                    {{ t('finance.approve') }}
                    </button>
                    <button class="reject-btn sm" :disabled="decisionBusy || !po.poNo" @click="openPoRejectModal(po.poNo)">
                      {{ t('finance.reject') }}
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="pendingPurchaseOrders.length === 0">
                <td colspan="6" class="empty-cell">{{ t('finance.match.empty_po_review') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-else-if="activeTab === 'review'">
        <header class="page-header">
          <div>
            <h1>{{ t('finance.match.title') }}</h1>
            <p>{{ t('finance.match.subtitle') }}</p>
          </div>
          <button class="secondary-btn" @click="refreshReviewQueue" :disabled="loadingList">
            {{ loadingList ? t('finance.match.loading') : t('finance.match.refresh') }}
          </button>
        </header>

        <div v-if="listError" class="empty-box error">{{ listError }}</div>

        <div class="list-toolbar">
          <label for="groupFilter">{{ t('finance.match.filter_group_status') }}</label>
          <select id="groupFilter" v-model="listFilter">
            <option value="all">{{ t('finance.match.all') }} ({{ activeReviewRows.length }})</option>
            <option value="complete">{{ t('finance.match.complete_docs') }} ({{ completeCount }})</option>
            <option value="waiting">{{ t('finance.match.waiting_docs') }} ({{ waitingCount }})</option>
            <option value="missing_gr_invoice">{{ t('finance.match.missing_gr_invoice') }} ({{ missingBothCount }})</option>
            <option value="missing_gr">{{ t('finance.match.missing_gr') }} ({{ missingGrCount }})</option>
            <option value="missing_invoice">{{ t('finance.match.missing_invoice') }} ({{ missingInvoiceCount }})</option>
            <option value="onHold">{{ t('finance.hold') }} ({{ onHoldCount }})</option>
          </select>
        </div>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('finance.match.po_no') }}</th>
                <th>{{ t('finance.match.vendor') }}</th>
                <th>{{ t('finance.match.po_date') }}</th>
                <th>{{ t('finance.match.goods_receipt') }}</th>
                <th>{{ t('finance.match.invoice') }}</th>
                <th>{{ t('finance.match.amount') }}</th>
                <th>{{ t('finance.status') }}</th>
                <th>{{ t('finance.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in filteredReviewRows" :key="row.poNo" :class="{ priority: row.isComplete }">
                <td class="key-cell">{{ row.poNo || '-' }}</td>
                <td>{{ row.vendorName || '-' }}</td>
                <td>{{ row.poDate || '-' }}</td>
                <td>
                  <span :class="['doc-pill', row.hasGr ? 'present' : 'missing']">
                    {{ row.grNo || (row.hasGr ? t('finance.match.uploaded') : t('finance.match.waiting_gr')) }}
                  </span>
                </td>
                <td>
                  <span :class="['doc-pill', row.hasInvoice ? 'present' : 'missing']">
                    {{ row.invoiceNo || (row.hasInvoice ? t('finance.match.uploaded') : t('finance.match.waiting_invoice')) }}
                  </span>
                </td>
                <td>{{ formatCurrency(row.totalAmount) }}</td>
                <td>
                  <span :class="['status-badge', row.statusKey]">{{ row.statusLabel }}</span>
                </td>
                <td>
                  <div class="row-actions">
                    <button class="primary-btn sm" :disabled="!row.poNo || !row.canReview" @click="openDetail(row.poNo, { row })">
                      {{ t('finance.match.enter_review') }}
                    </button>
                    <button class="reject-btn sm" :disabled="decisionBusy || !row.poNo" @click="voidGroup(row.poNo)">
                      {{ t('finance.match.void_group') }}
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="filteredReviewRows.length === 0">
                <td colspan="8" class="empty-cell">{{ t('finance.match.empty_list') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-else-if="activeTab === 'history'" class="history-panel">
        <header class="page-header">
          <div>
            <h1>{{ t('finance.match.history') }}</h1>
            <p>{{ t('finance.match.history_subtitle') }}</p>
          </div>
          <button class="secondary-btn" @click="loadLogs" :disabled="loadingLogs">
            {{ loadingLogs ? t('finance.match.loading') : t('finance.match.refresh') }}
          </button>
        </header>
        <h2 class="section-heading">{{ t('finance.match.approved_history') }}</h2>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{{ t('finance.match.time') }}</th>
                <th>{{ t('finance.match.po_no') }}</th>
                <th>{{ t('finance.status') }}</th>
                <th>{{ t('finance.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in approvedHistoryRows" :key="`${row.poNo}-${row.timestamp}`">
                <td>{{ formatDateTime(row.timestamp) }}</td>
                <td class="key-cell">{{ row.poNo || '-' }}</td>
                <td><span class="status-badge complete">{{ t('finance.approved') }}</span></td>
                <td>
                  <button class="primary-btn sm" :disabled="!row.poNo" @click="openHistoryDetail(row.poNo)">
                    {{ t('finance.match.view_detail') }}
                  </button>
                </td>
              </tr>
              <tr v-if="approvedHistoryRows.length === 0">
                <td colspan="4" class="empty-cell">{{ t('finance.match.empty_approved_history') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <h2 class="section-heading">{{ t('finance.match.operation_history') }}</h2>
        <LogTable :rows="financeLogs" :empty-text="t('finance.match.empty_history')" />
        <h2 class="section-heading">{{ t('finance.match.document_history') }}</h2>
        <DocumentHistoryTable :rows="documentHistoryRows" :empty-text="t('finance.match.empty_document_history')" />
      </div>

      <div v-else class="history-panel">
        <header class="page-header">
          <div>
            <h1>{{ t('finance.match.employee_operations') }}</h1>
            <p>{{ t('finance.match.employee_operations_subtitle') }}</p>
          </div>
          <button class="secondary-btn" @click="loadEmployeeOperations" :disabled="loadingOperations">
            {{ loadingOperations ? t('finance.match.loading') : t('finance.match.refresh') }}
          </button>
        </header>
        <OperationTable :rows="employeeOperationRows" :empty-text="t('finance.match.empty_employee_operations')" />
      </div>
    </section>

    <section v-else class="workbench">
      <header class="workbench-header">
        <button class="back-btn" @click="closeDetail">← {{ t('finance.match.back_to_list') }}</button>
        <div>
          <h1>{{ t('finance.match.detail_title') }} — {{ activePoNo }}</h1>
          <p>{{ activeDetail?.vendorName || '-' }}</p>
        </div>
        <div v-if="showDetailActions" class="workbench-actions">
          <button class="reject-btn" :disabled="decisionBusy" @click="showRejectModal = true">{{ t('finance.reject') }}</button>
        </div>
      </header>

      <div v-if="detailLoading" class="empty-box">{{ t('finance.match.detail_loading') }}</div>
      <div v-else-if="detailError" class="empty-box error">{{ detailError }}</div>
      <div v-else class="workbench-body">
        <aside class="preview-panel">
          <div class="doc-tabs">
            <button
              v-for="doc in previewDocs"
              :key="doc.key"
              :class="['doc-tab', activePreview === doc.key ? 'active' : '']"
              @click="activePreview = doc.key"
            >
              {{ doc.label }}
            </button>
          </div>

          <div class="preview-frame">
            <div class="preview-toolbar">
              <strong>{{ currentPreview.label }}</strong>
              <a v-if="currentPreview.url" :href="currentPreview.url" target="_blank" rel="noreferrer">{{ t('finance.match.open_new_tab') }}</a>
            </div>
            <object
              v-if="currentPreview.url"
              :key="`${currentPreview.key}-${currentPreview.url}`"
              :data="currentPreview.url"
              :type="currentPreview.type || 'application/pdf'"
              class="file-object"
            >
              <img :src="currentPreview.url" :alt="currentPreview.label" class="file-image" />
            </object>
            <div v-else class="empty-preview">{{ currentPreview.loading ? t('finance.match.file_loading') : t('finance.match.no_preview_file') }}</div>
          </div>
        </aside>

        <main class="compare-panel">
          <div class="review-meta">
            <div>
              <span>{{ t('finance.match.po_uploader') }}</span>
              <strong>{{ activeDetail?.po?.uploadedBy || '-' }}</strong>
            </div>
            <div>
              <span>{{ t('finance.match.gr_uploader') }}</span>
              <strong>{{ activeDetail?.gr?.uploadedBy || '-' }}</strong>
            </div>
            <div>
              <span>{{ t('finance.match.invoice_uploader') }}</span>
              <strong>{{ activeDetail?.invoice?.uploadedBy || '-' }}</strong>
            </div>
          </div>

          <section :class="['match-result-box', matchOutcome.status]">
            <div>
              <span>{{ t('finance.match.auto_match_result') }}</span>
              <strong>{{ matchOutcome.label }}</strong>
            </div>
            <p>{{ matchOutcome.description }}</p>
          </section>

          <section class="compare-section">
            <h2>{{ t('finance.match.compare_title') }}</h2>
            <table class="data-table compare-table">
              <thead>
                <tr>
                  <th>{{ t('finance.item_name') }}</th>
                  <th>{{ t('finance.match.po_ordered') }}</th>
                  <th>{{ t('finance.match.gr_received') }}</th>
                  <th>{{ t('finance.match.invoice_claimed') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="line in comparisonRows" :key="line.key">
                  <td class="key-cell">{{ line.itemName || '-' }}</td>
                  <td>
                    <LineValues :qty="line.poQty" :unit-price="line.poUnitPrice" />
                  </td>
                  <td>
                    <LineValues :qty="line.grQty" :unit-price="line.grUnitPrice" />
                  </td>
                  <td>
                    <LineValues :qty="line.invoiceQty" :unit-price="line.invoiceUnitPrice" />
                  </td>
                </tr>
                <tr v-if="comparisonRows.length === 0">
                  <td colspan="4" class="empty-cell">{{ t('finance.match.empty_compare') }}</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section class="totals-box">
            <div><span>項目加總金額</span><strong>{{ formatCurrency(invoiceSubtotal) }}</strong></div>
            <div v-if="invoiceHasTax"><span>{{ taxLabel }}</span><strong>{{ formatCurrency(invoiceTax) }}</strong></div>
            <div><span>明細金額</span><strong>{{ formatCurrency(invoiceTotal) }}</strong></div>
            <div class="grand"><span>採購單金額</span><strong>{{ formatCurrency(poTotal) }}</strong></div>
          </section>
        </main>
      </div>
    </section>

    <transition name="fade">
      <div v-if="poPreview.show" class="modal-overlay" @click.self="closePurchaseOrderPreview">
        <div class="modal-box preview-modal">
          <div class="preview-modal-header">
            <div>
              <h2>{{ t('finance.match.purchase_order') }}</h2>
              <p>{{ poPreview.poNo }}</p>
            </div>
            <button class="secondary-btn sm" @click="closePurchaseOrderPreview">{{ t('finance.cancel') }}</button>
          </div>
          <div class="preview-toolbar modal-preview-toolbar">
            <strong>{{ poPreview.poNo }}</strong>
            <a v-if="poPreview.url" :href="poPreview.url" target="_blank" rel="noreferrer">{{ t('finance.match.open_new_tab') }}</a>
          </div>
          <div class="preview-frame po-preview-frame">
            <object
              v-if="poPreview.url"
              :data="poPreview.url"
              :type="poPreview.type || 'application/pdf'"
              class="file-object"
            >
              <img :src="poPreview.url" :alt="poPreview.poNo" class="file-image" />
            </object>
            <div v-else class="empty-preview">
              {{ poPreview.loading ? t('finance.match.file_loading') : poPreview.error || t('finance.match.no_preview_file') }}
            </div>
          </div>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div v-if="showPoRejectModal" class="modal-overlay" @click.self="showPoRejectModal = false">
        <div class="modal-box">
          <h2>{{ t('finance.match.reject_po_title') }}</h2>
          <p>{{ poRejectNo }}</p>
          <label for="poRejectReason">{{ t('finance.reject_reason_label') }}</label>
          <textarea id="poRejectReason" v-model="poRejectReason" rows="4" :placeholder="t('finance.reject_reason_placeholder')"></textarea>
          <div class="modal-actions">
            <button class="secondary-btn" @click="showPoRejectModal = false">{{ t('finance.cancel') }}</button>
            <button class="reject-btn" :disabled="!poRejectReason.trim() || decisionBusy" @click="confirmRejectPurchaseOrder">{{ t('finance.reject_confirm') }}</button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="fade">
        <div v-if="showRejectModal" class="modal-overlay" @click.self="showRejectModal = false">
        <div class="modal-box">
          <h2>{{ t('finance.match.reject_doc_title') }}</h2>
          <p>{{ activePoNo }}</p>
          <label for="rejectDocType">{{ t('finance.match.reject_doc_label') }}</label>
          <select id="rejectDocType" v-model="rejectDocType">
            <option value="invoice">{{ t('finance.match.invoice') }}</option>
          </select>
          <label for="rejectReason">{{ t('finance.reject_reason_label') }}</label>
          <textarea id="rejectReason" v-model="rejectReason" rows="4" :placeholder="t('finance.reject_reason_placeholder')"></textarea>
          <div class="modal-actions">
            <button class="secondary-btn" @click="showRejectModal = false">{{ t('finance.cancel') }}</button>
            <button class="reject-btn" :disabled="!rejectReason.trim() || decisionBusy" @click="confirmReject">{{ t('finance.reject_confirm') }}</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { apiFetch } from '@/api.js';

const TOLERANCE_RATE = 0.01;
const AUTO_REVIEW_INTERVAL_MS = 5000;
const { t } = useI18n();
const useMockFallback = import.meta.env.VITE_API_MOCK_ENABLED === 'true';

const LineValues = defineComponent({
  props: {
    qty: { type: [Number, String], default: 0 },
    unitPrice: { type: [Number, String], default: 0 },
  },
  setup(props) {
    return () => h('div', { class: 'line-values' }, [
      h('div', [h('span', t('finance.qty')), h('strong', String(props.qty ?? 0))]),
      h('div', [h('span', t('finance.unit_price')), h('strong', formatCurrency(props.unitPrice))]),
    ]);
  },
});

const LogTable = defineComponent({
  props: {
    rows: { type: Array, default: () => [] },
    emptyText: { type: String, default: '' },
  },
  setup(props) {
    return () => props.rows.length
      ? h('div', { class: 'table-wrap' }, [
          h('table', { class: 'data-table' }, [
            h('thead', [
              h('tr', [
                h('th', t('finance.match.time')),
                h('th', t('finance.match.po_no')),
                h('th', t('finance.actions')),
                h('th', t('finance.match.document')),
                h('th', t('finance.match.remark')),
              ]),
            ]),
            h('tbody', props.rows.map((row, index) => h('tr', { key: `${row.timestamp}-${index}` }, [
              h('td', formatDateTime(row.timestamp)),
              h('td', row.poNo || '-'),
              h('td', row.actionType || '-'),
              h('td', row.docType || '-'),
              h('td', row.remark || '-'),
            ]))),
          ]),
        ])
      : h('div', { class: 'empty-box' }, props.emptyText || t('finance.match.empty_record'));
  },
});

const DocumentHistoryTable = defineComponent({
  props: {
    rows: { type: Array, default: () => [] },
    emptyText: { type: String, default: '' },
  },
  setup(props) {
    return () => props.rows.length
      ? h('div', { class: 'table-wrap' }, [
          h('table', { class: 'data-table' }, [
            h('thead', [
              h('tr', [
                h('th', t('finance.match.document')),
                h('th', t('finance.match.doc_no')),
                h('th', t('finance.status')),
                h('th', t('finance.match.uploaded_by')),
                h('th', t('finance.match.vendor')),
                h('th', t('finance.match.amount')),
                h('th', t('finance.match.updated_at')),
              ]),
            ]),
            h('tbody', props.rows.map(row => h('tr', { key: `${row.docType}-${row.docNo}-${row.updatedAt}` }, [
              h('td', documentTypeLabel(row.docType)),
              h('td', row.docNo || '-'),
              h('td', row.status || '-'),
              h('td', row.uploadedBy || row.employeeName || '-'),
              h('td', row.vendorName || '-'),
              h('td', formatCurrency(row.totalAmount)),
              h('td', formatDateTime(row.updatedAt || row.submittedAt)),
            ]))),
          ]),
        ])
      : h('div', { class: 'empty-box' }, props.emptyText || t('finance.match.empty_record'));
  },
});

const OperationTable = defineComponent({
  props: {
    rows: { type: Array, default: () => [] },
    emptyText: { type: String, default: '' },
  },
  setup(props) {
    return () => props.rows.length
      ? h('div', { class: 'table-wrap' }, [
          h('table', { class: 'data-table' }, [
            h('thead', [
              h('tr', [
                h('th', t('finance.match.time')),
                h('th', t('finance.match.actor')),
                h('th', t('finance.match.document')),
                h('th', t('finance.match.doc_no')),
                h('th', t('finance.actions')),
                h('th', t('finance.status')),
                h('th', t('finance.match.remark')),
              ]),
            ]),
            h('tbody', props.rows.map((row, index) => h('tr', { key: `${row.actedAt}-${row.docNo}-${index}` }, [
              h('td', formatDateTime(row.actedAt)),
              h('td', row.actorName || row.actorEmail || '-'),
              h('td', documentTypeLabel(row.docType)),
              h('td', row.docNo || '-'),
              h('td', row.actionType || row.recordType || '-'),
              h('td', row.status || row.toStatus || '-'),
              h('td', row.comment || '-'),
            ]))),
          ]),
        ])
      : h('div', { class: 'empty-box' }, props.emptyText || t('finance.match.empty_record'));
  },
});

const activeTab = ref('poReview');
const listFilter = ref('all');
const pendingPurchaseOrders = ref([]);
const reviewRows = ref([]);
const financeLogs = ref([]);
const documentHistoryRows = ref([]);
const employeeOperationRows = ref([]);
const loadingPoList = ref(false);
const loadingList = ref(false);
const loadingLogs = ref(false);
const loadingOperations = ref(false);
const historyLoaded = ref(false);
const operationsLoaded = ref(false);
const poListError = ref('');
const listError = ref('');

const activePoNo = ref('');
const activeDetail = ref(null);
const activeReviewContext = ref(null);
const detailReadOnly = ref(false);
const detailLoading = ref(false);
const detailError = ref('');
const activePreview = ref('invoice');
const previewState = ref({
  invoice: { url: '', type: '', loading: false },
  po: { url: '', type: '', loading: false },
  gr: { url: '', type: '', loading: false },
});
const poPreview = ref({ show: false, poNo: '', url: '', type: '', loading: false, error: '' });
const objectUrls = new Set();

const decisionBusy = ref(false);
const showRejectModal = ref(false);
const rejectDocType = ref('invoice');
const rejectReason = ref('');
const showPoRejectModal = ref(false);
const poRejectNo = ref('');
const poRejectReason = ref('');
const autoReviewingPoNos = new Set();
const autoReviewBlockedSignatures = new Map();
let autoReviewTimer = null;
let queueRefreshInFlight = false;

const fallbackRows = [
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
];

const fallbackDetails = {
  'PO-8801': {
    poNo: 'PO-8801',
    vendorName: '宏遠科技',
    groupStatus: 'pending',
    po: {
      uploadedBy: '王小明',
      totalAmount: 625000,
      items: [
        { lineNo: 1, itemName: '筆記型電腦', quantity: 10, unitPrice: 60000 },
        { lineNo: 2, itemName: '無線滑鼠', quantity: 10, unitPrice: 2500 },
      ],
    },
    gr: {
      uploadedBy: '陳怡君',
      items: [
        { lineNo: 1, itemName: '筆記型電腦', receivedQty: 10, acceptedQty: 10, lineAmount: 600000 },
        { lineNo: 2, itemName: '無線滑鼠', receivedQty: 10, acceptedQty: 10, lineAmount: 25000 },
      ],
    },
    invoice: {
      uploadedBy: '林志豪',
      invoiceNo: 'INV-2026-001',
      totalAmount: 625000,
      items: [
        { lineNo: 1, itemName: '筆記型電腦', quantity: 10, unitPrice: 60000 },
        { lineNo: 2, itemName: '無線滑鼠', quantity: 10, unitPrice: 2500 },
      ],
    },
    comparisonItems: [
      { itemName: '筆記型電腦', poQty: 10, poUnitPrice: 60000, grQty: 10, grUnitPrice: 60000, invoiceQty: 10, invoiceUnitPrice: 60000 },
      { itemName: '無線滑鼠', poQty: 10, poUnitPrice: 2500, grQty: 10, grUnitPrice: 2500, invoiceQty: 10, invoiceUnitPrice: 2500 },
    ],
  },
};

const normalizedRows = computed(() => reviewRows.value.map(normalizeReviewRow));
const pendingPoNos = computed(() => new Set(pendingPurchaseOrders.value
  .map(row => row.poNo || row.po_no || row.poId || row.po_id)
  .filter(Boolean)));
const approvedHistoryRows = computed(() => {
  const rows = financeLogs.value
    .filter(isApprovedMatchGroupAction)
    .sort((a, b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0));
  const seen = new Set();
  return rows.filter(row => {
    if (seen.has(row.poNo)) return false;
    seen.add(row.poNo);
    return true;
  });
});
const approvedHistoryPoNos = computed(() => new Set(approvedHistoryRows.value.map(row => row.poNo)));
const activeReviewRows = computed(() => normalizedRows.value.filter(row => (
  hasApprovedPurchaseOrder(row)
    && !approvedHistoryPoNos.value.has(row.poNo)
    && !['approved', 'void'].includes(row.groupStatus)
)));
const completeCount = computed(() => activeReviewRows.value.filter(row => row.isComplete).length);
const waitingCount = computed(() => activeReviewRows.value.filter(row => !row.isComplete).length);
const missingGrCount = computed(() => activeReviewRows.value.filter(row => row.missingDocs.includes('goodsReceipt')).length);
const missingInvoiceCount = computed(() => activeReviewRows.value.filter(row => row.missingDocs.includes('invoice')).length);
const missingBothCount = computed(() => activeReviewRows.value.filter(row => row.missingDocs.includes('goodsReceipt') && row.missingDocs.includes('invoice')).length);
const onHoldCount = computed(() => activeReviewRows.value.filter(row => row.groupStatus === 'onHold').length);
const filteredReviewRows = computed(() => {
  const rows = activeReviewRows.value
    .filter(row => {
      if (listFilter.value === 'complete') return row.isComplete && row.groupStatus !== 'onHold';
      if (listFilter.value === 'waiting') return !row.isComplete && row.groupStatus !== 'onHold';
      if (listFilter.value === 'missing_gr_invoice') return row.missingDocs.includes('goodsReceipt') && row.missingDocs.includes('invoice');
      if (listFilter.value === 'missing_gr') return row.missingDocs.includes('goodsReceipt');
      if (listFilter.value === 'missing_invoice') return row.missingDocs.includes('invoice');
      if (listFilter.value === 'onHold') return row.groupStatus === 'onHold';
      return true;
    })
    .sort((a, b) => (Number(b.isComplete) - Number(a.isComplete)) || ((b.priority ?? 0) - (a.priority ?? 0)));
  return rows;
});

const previewDocs = computed(() => [
  { key: 'invoice', label: t('finance.match.invoice'), ...previewState.value.invoice },
  { key: 'po', label: t('finance.match.purchase_order'), ...previewState.value.po },
  { key: 'gr', label: t('finance.match.goods_receipt'), ...previewState.value.gr },
]);
const currentPreview = computed(() => previewDocs.value.find(doc => doc.key === activePreview.value) || previewDocs.value[0]);

const comparisonRows = computed(() => buildComparisonRows(activeDetail.value?.comparisonItems || []));
const backendMatchResult = computed(() => activeDetail.value?.matchResult || null);
const backendMatchIssues = computed(() => (
  Array.isArray(backendMatchResult.value?.issues)
    ? backendMatchResult.value.issues.map(issue => issue?.message || issue).filter(Boolean)
    : []
));

function buildComparisonRows(rows) {
  return rows.map((line, index) => {
    const qtyOk = numberValue(line.poQty) === numberValue(line.grQty) && numberValue(line.poQty) === numberValue(line.invoiceQty);
    const basePrice = numberValue(line.poUnitPrice);
    const invoicePrice = numberValue(line.invoiceUnitPrice);
    const grPrice = numberValue(line.grUnitPrice);
    const invoiceDiff = Math.abs(invoicePrice - basePrice);
    const grDiff = Math.abs(grPrice - basePrice);
    const tolerance = Math.abs(basePrice) * TOLERANCE_RATE;
    let status = 'ok';
    let statusLabel = t('finance.match.line_ok');
    const issues = [];
    if (!qtyOk) {
      issues.push(t('finance.match.qty_mismatch_detail', {
        po: numberValue(line.poQty),
        gr: numberValue(line.grQty),
        invoice: numberValue(line.invoiceQty),
      }));
    }
    if (invoiceDiff > tolerance) {
      issues.push(t('finance.match.invoice_price_mismatch_detail', {
        po: formatCurrency(basePrice),
        invoice: formatCurrency(invoicePrice),
      }));
    }
    if (grDiff > tolerance) {
      issues.push(t('finance.match.gr_price_mismatch_detail', {
        po: formatCurrency(basePrice),
        gr: formatCurrency(grPrice),
      }));
    }
    if (!qtyOk || invoiceDiff > tolerance || grDiff > tolerance) {
      status = 'mismatch';
      statusLabel = t('finance.match.line_mismatch');
    } else if (invoiceDiff > 0 || grDiff > 0) {
      status = 'tolerance';
      statusLabel = t('finance.match.line_tolerance');
      issues.push(t('finance.match.within_tolerance_detail'));
    }
    return { ...line, key: `${line.itemName || 'line'}-${index}`, status, statusLabel, issueText: issues.join(t('finance.match.list_separator')) };
  });
}

const hasMismatch = computed(() => backendMatchResult.value?.status === 'mismatch' || comparisonRows.value.some(row => row.status === 'mismatch'));
const showDetailActions = computed(() => !detailReadOnly.value && !['approved', 'void'].includes(activeDetail.value?.groupStatus));
const matchOutcome = computed(() => {
  if (!comparisonRows.value.length) {
    return {
      status: 'waiting',
      label: t('finance.match.waiting_data'),
      description: t('finance.match.auto_match_waiting'),
    };
  }
  if (hasMismatch.value) {
    return {
      status: 'mismatch',
      label: activeDetail.value?.groupStatus === 'onHold' ? t('finance.hold') : t('finance.match.line_mismatch'),
      description: backendMatchIssues.value.length
        ? backendMatchIssues.value.join(t('finance.match.list_separator'))
        : t('finance.match.auto_match_mismatch'),
    };
  }
  return {
    status: 'ok',
    label: t('finance.match.line_ok'),
    description: t('finance.match.auto_match_ok'),
  };
});
const invoiceSubtotal = computed(() => comparisonRows.value.reduce((sum, line) => (
  sum + numberValue(line.invoiceQty) * numberValue(line.invoiceUnitPrice)
), 0));
const invoiceTaxRaw = computed(() => firstNonEmpty(
  activeDetail.value?.invoice?.taxAmount,
  activeDetail.value?.invoice?.tax_amount,
));
const invoiceTaxRateRaw = computed(() => firstNonEmpty(
  activeDetail.value?.invoice?.taxRate,
  activeDetail.value?.invoice?.tax_rate,
));
const invoiceHasTax = computed(() => invoiceTaxRaw.value !== null && invoiceTaxRaw.value !== undefined && invoiceTaxRaw.value !== '');
const invoiceTax = computed(() => (invoiceHasTax.value ? numberValue(invoiceTaxRaw.value) : 0));
const taxLabel = computed(() => {
  if (invoiceTaxRateRaw.value === null || invoiceTaxRateRaw.value === undefined || invoiceTaxRateRaw.value === '') {
    return t('finance.tax');
  }
  return `${t('finance.tax')} (${numberValue(invoiceTaxRateRaw.value) * 100}%)`;
});
const invoiceTotal = computed(() => {
  const explicitTotal = firstNonEmpty(activeDetail.value?.invoice?.totalAmount, activeDetail.value?.invoice?.total_amount);
  if (explicitTotal !== null && explicitTotal !== undefined && explicitTotal !== '') return numberValue(explicitTotal);
  return invoiceSubtotal.value + invoiceTax.value;
});

const poTotal = computed(() => {
  const explicitTotal = firstNonEmpty(activeDetail.value?.po?.totalAmount, activeDetail.value?.po?.total_amount);
  if (explicitTotal !== null && explicitTotal !== undefined && explicitTotal !== '') return numberValue(explicitTotal);
  
  return comparisonRows.value.reduce((sum, line) => (
    sum + numberValue(line.poQty) * numberValue(line.poUnitPrice)
  ), 0);
});

onMounted(async () => {
  await Promise.all([loadPendingPurchaseOrders(), loadReviewList(), loadLogs()]);
  await autoReviewReadyGroups();
  startAutoReviewScheduler();
});

onBeforeUnmount(() => {
  stopAutoReviewScheduler();
  revokePreviewUrls();
});

function normalizeReviewRow(row) {
  const purchaseOrder = row.purchaseOrder || row.purchase_order || {};
  const goodsReceipt = row.goodsReceipt || row.goods_receipt || {};
  const invoice = row.invoice || {};
  const rawGroupStatus = normalizeStatus(row.groupStatus || row.group_status || row.status || 'pending');
  const poStatus = normalizeStatus(row.poStatus || row.po_status || purchaseOrder.status || purchaseOrder.poStatus || purchaseOrder.po_status || '');
  const poNo = row.poNo || row.po_no || purchaseOrder.poNo || purchaseOrder.po_no || '';
  const grStatus = normalizeStatus(row.grStatus || row.gr_status || goodsReceipt.status || goodsReceipt.grStatus || goodsReceipt.gr_status || '');
  const invoiceStatus = normalizeStatus(row.invoiceStatus || row.invoice_status || invoice.status || invoice.invoiceStatus || invoice.invoice_status || '');
  const hasResubmittedDocument = [grStatus, invoiceStatus].some(isRematchCandidateStatus);
  const groupStatus = rawGroupStatus === 'onHold' && hasResubmittedDocument ? 'pendingMatch' : rawGroupStatus;
  const invoiceNo = firstNonEmpty(row.invoiceNo, row.invoice_no, invoice.invoiceNo, invoice.invoice_no, invoice.docNo, invoice.doc_no);
  const grNo = firstNonEmpty(
    row.grNo,
    row.gr_no,
    row.goodsReceiptNo,
    row.goods_receipt_no,
    goodsReceipt.grNo,
    goodsReceipt.gr_no,
    goodsReceipt.docNo,
    goodsReceipt.doc_no,
    goodsReceipt.receiptNo,
    goodsReceipt.receipt_no,
    goodsReceipt.goodsReceiptNo,
    goodsReceipt.goods_receipt_no,
  );
  const rawMissingDocs = normalizeMissingDocs(row.missingDocuments || row.missing_documents, { invoiceNo, grNo });
  const readyForMatch = Boolean(row.readyForMatch || row.ready_for_match || groupStatus === 'complete');
  const hasGr = Boolean(grNo || readyForMatch || objectHasData(goodsReceipt) || !rawMissingDocs.includes('goodsReceipt'));
  const hasInvoice = Boolean(invoiceNo || readyForMatch || objectHasData(invoice) || !rawMissingDocs.includes('invoice'));
  const missingDocs = rawMissingDocs.filter(docType => {
    if (docType === 'goodsReceipt') return !hasGr;
    if (docType === 'invoice') return !hasInvoice;
    return true;
  });
  const isComplete = Boolean(readyForMatch || (poNo && hasInvoice && hasGr));
  const statusKey = groupStatus === 'onHold'
    ? 'onHold'
    : groupStatus === 'approved'
      ? 'complete'
      : isComplete
        ? 'complete'
        : 'waiting';
  const statusLabel = groupStatus === 'approved'
    ? t('finance.approved')
    : groupStatus === 'onHold'
      ? t('finance.hold')
      : isComplete
        ? t('finance.match.complete_docs')
        : missingLabel(missingDocs);
  const reviewRow = {
    poNo,
    vendorName: row.vendorName || row.vendor_name || purchaseOrder.vendorName || purchaseOrder.vendor_name || '',
    poDate: firstNonEmpty(
      row.poDate,
      row.po_date,
      row.purchaseDate,
      row.purchase_date,
      row.orderDate,
      row.order_date,
      purchaseOrder.poDate,
      purchaseOrder.po_date,
      purchaseOrder.purchaseDate,
      purchaseOrder.purchase_date,
      purchaseOrder.orderDate,
      purchaseOrder.order_date,
      '',
    ),
    invoiceNo,
    invoiceDate: row.invoiceDate || row.invoice_date || invoice.invoiceDate || invoice.invoice_date || '',
    grNo,
    hasGr,
    hasInvoice,
    totalAmount: row.totalAmount ?? row.total_amount ?? invoice.totalAmount ?? invoice.total_amount ?? purchaseOrder.totalAmount ?? purchaseOrder.total_amount ?? 0,
    groupStatus,
    rawGroupStatus,
    poStatus,
    grStatus,
    invoiceStatus,
    autoReviewSignature: autoReviewSignature(row, { poNo, grNo, invoiceNo, groupStatus, rawGroupStatus, poStatus, grStatus, invoiceStatus }),
    missingDocs,
    priority: row.priority ?? 0,
    isComplete,
    statusKey,
    statusLabel,
  };
  return { ...reviewRow, canReview: canReviewGroup(reviewRow) };
}

function canReviewGroup(row) {
  if (!row?.isComplete) return false;
  if (['approved', 'void', 'rejected'].includes(row.groupStatus)) return false;
  if (row.groupStatus === 'po_pending') return false;
  if (!hasApprovedPurchaseOrder(row)) return false;
  return true;
}

function canAutoReviewRow(row) {
  if (!canReviewGroup(row)) return false;
  return ['complete', 'pending', 'pendingMatch'].includes(row.groupStatus)
    || (row.rawGroupStatus === 'onHold' && [row.grStatus, row.invoiceStatus].some(isRematchCandidateStatus));
}

function isRematchCandidateStatus(status) {
  return ['pending', 'pendingMatch'].includes(status);
}

function isApprovedMatchGroupAction(row) {
  if (!row?.poNo) return false;
  const actionType = normalizeActionToken(row.actionType || row.action_type || row.action);
  if (actionType !== 'approve') return false;
  const docType = normalizeActionToken(row.docType || row.doc_type || row.targetType || row.target_type);
  return !docType || docType === 'matchgroup' || docType === 'matchgroups';
}

function normalizeActionToken(value) {
  return String(value || '').trim().replace(/[_\-\s]/g, '').toLowerCase();
}

function hasApprovedPurchaseOrder(row) {
  if (!row?.poNo) return false;
  if (row.poStatus) return row.poStatus === 'approved';
  return !pendingPoNos.value.has(row.poNo) && row.groupStatus !== 'po_pending';
}

function normalizeStatus(status) {
  if (status === 'on_hold') return 'onHold';
  if (status === 'pending_match') return 'pendingMatch';
  return status || '';
}

function autoReviewSignature(row, normalized) {
  const purchaseOrder = row.purchaseOrder || row.purchase_order || {};
  const goodsReceipt = row.goodsReceipt || row.goods_receipt || {};
  const invoice = row.invoice || {};
  return stableStringify({
    poNo: normalized.poNo,
    grNo: normalized.grNo,
    invoiceNo: normalized.invoiceNo,
    groupStatus: normalized.groupStatus,
    poStatus: normalized.poStatus,
    grStatus: normalized.grStatus,
    invoiceStatus: normalized.invoiceStatus,
    rawGroupStatus: normalized.rawGroupStatus,
    groupUpdatedAt: firstNonEmpty(row.updatedAt, row.updated_at, row.groupUpdatedAt, row.group_updated_at),
    grId: firstNonEmpty(row.grId, row.gr_id, goodsReceipt.grId, goodsReceipt.gr_id, goodsReceipt.id),
    grTotalAmount: firstNonEmpty(row.grTotalAmount, row.gr_total_amount, goodsReceipt.totalAmount, goodsReceipt.total_amount),
    grUpdatedAt: firstNonEmpty(goodsReceipt.updatedAt, goodsReceipt.updated_at, goodsReceipt.uploadedAt, goodsReceipt.uploaded_at),
    grFile: firstNonEmpty(goodsReceipt.storagePath, goodsReceipt.storage_path, goodsReceipt.filePath, goodsReceipt.file_path, goodsReceipt.latestFile),
    invoiceId: firstNonEmpty(row.invoiceId, row.invoice_id, invoice.invoiceId, invoice.invoice_id, invoice.id),
    invoiceTotalAmount: firstNonEmpty(row.invoiceTotalAmount, row.invoice_total_amount, invoice.totalAmount, invoice.total_amount),
    invoiceTaxAmount: firstNonEmpty(invoice.taxAmount, invoice.tax_amount),
    invoiceUpdatedAt: firstNonEmpty(invoice.updatedAt, invoice.updated_at, invoice.uploadedAt, invoice.uploaded_at),
    invoiceFile: firstNonEmpty(invoice.storagePath, invoice.storage_path, invoice.filePath, invoice.file_path, invoice.latestFile),
  });
}

function stableStringify(value) {
  if (!value || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`;
}

function firstNonEmpty(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '') || null;
}

function objectHasData(value) {
  return value && typeof value === 'object' && Object.keys(value).length > 0;
}

function normalizeMissingDocs(rawMissing, row) {
  const docs = Array.isArray(rawMissing) ? rawMissing.map(item => String(item)) : [];
  if (!docs.length) {
    if (!row.grNo) docs.push('goodsReceipt');
    if (!row.invoiceNo) docs.push('invoice');
  }
  return docs.map(item => {
    if (['gr', 'goods_receipt', 'goodsReceipt'].includes(item)) return 'goodsReceipt';
    if (['inv', 'invoice'].includes(item)) return 'invoice';
    if (['po', 'purchase_order', 'purchaseOrder'].includes(item)) return 'purchaseOrder';
    return item;
  });
}

function missingLabel(missingDocs) {
  const missing = missingDocs.map(documentTypeLabel);
  return missing.length ? t('finance.match.waiting_specific_docs', { docs: missing.join(t('finance.match.list_separator')) }) : t('finance.match.waiting_data');
}

async function switchTab(tab) {
  activeTab.value = tab;
  if (tab === 'history' && !historyLoaded.value) {
    await loadDocumentHistory();
  }
  if (tab === 'operations' && !operationsLoaded.value) {
    await loadEmployeeOperations();
  }
}

function startAutoReviewScheduler() {
  stopAutoReviewScheduler();
  autoReviewTimer = window.setInterval(() => {
    refreshReviewQueue({ silent: true });
  }, AUTO_REVIEW_INTERVAL_MS);
}

function stopAutoReviewScheduler() {
  if (autoReviewTimer) {
    window.clearInterval(autoReviewTimer);
    autoReviewTimer = null;
  }
}

async function refreshReviewQueue(options = {}) {
  if (queueRefreshInFlight || activePoNo.value) return;
  queueRefreshInFlight = true;
  try {
    await Promise.all([
      loadReviewList({ silent: options.silent }),
      loadLogs({ silent: options.silent }),
    ]);
    await autoReviewReadyGroups();
  } finally {
    queueRefreshInFlight = false;
  }
}

async function autoReviewReadyGroups() {
  if (activePoNo.value) return;
  const candidates = activeReviewRows.value.filter(row => canAutoReviewRow(row) && shouldAutoReviewRow(row));
  for (const row of candidates) {
    await autoReviewGroup(row);
  }
}

function shouldAutoReviewRow(row) {
  if (!row?.poNo) return false;
  return autoReviewBlockedSignatures.get(row.poNo) !== row.autoReviewSignature;
}

async function autoReviewGroup(row) {
  if (!row?.poNo || autoReviewingPoNos.has(row.poNo)) return;
  autoReviewingPoNos.add(row.poNo);
  try {
    const decisionResponse = await apiFetch(`/finance/match-groups/${encodeURIComponent(row.poNo)}/auto-review`, { method: 'POST' });
    if (!decisionResponse.ok) throw new Error(await decisionResponse.text());
    const decision = await decisionResponse.json();
    if (decision.matchStatus === 'waiting') return;

    const groupStatus = normalizeStatus(decision.groupStatus || (decision.matched ? 'approved' : 'onHold'));
    if (!decision.matched) {
      autoReviewBlockedSignatures.set(row.poNo, row.autoReviewSignature);
    } else {
      autoReviewBlockedSignatures.delete(row.poNo);
    }
    updateLocalGroupStatus(row.poNo, groupStatus);
    if (activePoNo.value === row.poNo && activeDetail.value) {
      activeDetail.value = { ...activeDetail.value, groupStatus };
    }
    await Promise.all([
      loadLogs({ silent: true }),
      loadReviewList({ silent: true }),
      decision.matched ? loadDocumentHistory() : Promise.resolve(),
    ]);
  } catch (error) {
    console.warn('Background auto review failed:', error);
  } finally {
    autoReviewingPoNos.delete(row.poNo);
  }
}

async function loadPendingPurchaseOrders(options = {}) {
  if (!options.silent) {
    loadingPoList.value = true;
    poListError.value = '';
  }
  try {
    const response = await apiFetch('/finance/purchase-orders/pending');
    if (!response.ok) throw new Error(await response.text());
    pendingPurchaseOrders.value = await response.json();
  } catch (error) {
    console.error('Failed to load pending purchase orders:', error);
    if (!options.silent) {
      pendingPurchaseOrders.value = [];
      poListError.value = t('finance.match.load_po_failed', { message: error.message });
    }
  } finally {
    if (!options.silent) loadingPoList.value = false;
  }
}

async function loadReviewList(options = {}) {
  if (!options.silent) {
    loadingList.value = true;
    listError.value = '';
  }
  try {
    const response = await apiFetch('/finance/po-review-groups?limit=100');
    if (!response.ok) throw new Error(await response.text());
    reviewRows.value = await response.json();
  } catch (error) {
    if (useMockFallback) {
      console.warn('Using finance fallback rows:', error);
      reviewRows.value = fallbackRows;
    } else {
      console.error('Failed to load finance match groups:', error);
      if (!options.silent) {
        reviewRows.value = [];
        listError.value = t('finance.match.load_list_failed', { message: error.message });
      }
    }
  } finally {
    if (!options.silent) loadingList.value = false;
  }
}

async function loadLogs(options = {}) {
  if (!options.silent) loadingLogs.value = true;
  try {
    const response = await apiFetch('/finance/logs');
    if (!response.ok) throw new Error(await response.text());
    financeLogs.value = await response.json();
  } catch (error) {
    console.warn('Failed to load finance logs:', error);
    if (!options.silent) financeLogs.value = [];
  } finally {
    if (!options.silent) loadingLogs.value = false;
  }
}

async function loadDocumentHistory() {
  try {
    const response = await apiFetch('/finance/document-history?limit=100');
    if (!response.ok) throw new Error(await response.text());
    documentHistoryRows.value = await response.json();
    historyLoaded.value = true;
  } catch (error) {
    console.warn('Failed to load document history:', error);
    documentHistoryRows.value = [];
    historyLoaded.value = false;
  }
}

async function loadEmployeeOperations() {
  loadingOperations.value = true;
  try {
    const response = await apiFetch('/finance/employee-operation-records?limit=100');
    if (!response.ok) throw new Error(await response.text());
    employeeOperationRows.value = await response.json();
    operationsLoaded.value = true;
  } catch (error) {
    console.warn('Failed to load employee operation records:', error);
    employeeOperationRows.value = [];
    operationsLoaded.value = false;
  } finally {
    loadingOperations.value = false;
  }
}

async function openDetail(poNo, options = {}) {
  detailReadOnly.value = Boolean(options.readOnly);
  activeReviewContext.value = detailReadOnly.value
    ? null
    : (options.row || normalizedRows.value.find(row => row.poNo === poNo) || null);
  activePoNo.value = poNo;
  activeDetail.value = null;
  detailError.value = '';
  detailLoading.value = true;
  activePreview.value = 'invoice';
  revokePreviewUrls();
  resetPreviewState();

  try {
    const response = await apiFetch(`/finance/match-groups/${encodeURIComponent(poNo)}`);
    if (!response.ok) throw new Error(await response.text());
    activeDetail.value = await response.json();
  } catch (error) {
    if (useMockFallback) {
      console.warn('Using finance fallback detail:', error);
      activeDetail.value = fallbackDetails[poNo] || null;
      if (!activeDetail.value) detailError.value = t('finance.match.load_detail_failed');
    } else {
      console.error('Failed to load finance match group detail:', error);
      activeDetail.value = null;
      detailError.value = t('finance.match.load_detail_failed_with_message', { message: error.message });
    }
  } finally {
    detailLoading.value = false;
  }

  if (activeDetail.value) {
    if (!detailReadOnly.value) {
      const reviewResult = await runBackendAutoReview(poNo, activeReviewContext.value);
      if (reviewResult?.matched) {
        activeTab.value = 'history';
        closeDetail();
        return;
      }
    }
    await loadPreviewFiles(poNo);
  }
}

function openHistoryDetail(poNo) {
  openDetail(poNo, { readOnly: true });
}

function closeDetail() {
  activePoNo.value = '';
  activeDetail.value = null;
  activeReviewContext.value = null;
  detailReadOnly.value = false;
  detailError.value = '';
  showRejectModal.value = false;
  rejectReason.value = '';
  revokePreviewUrls();
  resetPreviewState();
}

function resetPreviewState() {
  previewState.value = {
    invoice: { url: '', type: '', loading: false },
    po: { url: '', type: '', loading: false },
    gr: { url: '', type: '', loading: false },
  };
}

async function loadPreviewFiles(poNo) {
  await Promise.all([
    loadPreviewFile('invoice', `/finance/match-groups/${encodeURIComponent(poNo)}/invoice/file`, '/invoices/INV-2026-001.svg'),
    loadPreviewFile('po', `/finance/match-groups/${encodeURIComponent(poNo)}/po/file`, '/invoices/sample_purchase_order.png'),
    loadPreviewFile('gr', `/finance/match-groups/${encodeURIComponent(poNo)}/gr/file`, '/invoices/sample_goods_receipt.png'),
  ]);
}

async function runBackendAutoReview(poNo, context) {
  if (!canAutoReviewRow(context)) return null;
  if (!shouldAutoReviewRow(context)) return null;
  try {
    const response = await apiFetch(`/finance/match-groups/${encodeURIComponent(poNo)}/auto-review`, { method: 'POST' });
    if (!response.ok) throw new Error(await response.text());
    const result = await response.json();
    if (result.matchStatus === 'waiting') return result;

    const groupStatus = normalizeStatus(result.groupStatus || (result.matched ? 'approved' : 'onHold'));
    activeDetail.value = {
      ...activeDetail.value,
      groupStatus,
      matchResult: {
        matched: Boolean(result.matched),
        status: result.matchStatus,
        issues: result.issues || [],
      },
    };
    updateLocalGroupStatus(poNo, groupStatus);
    if (result.matched) {
      autoReviewBlockedSignatures.delete(poNo);
      await Promise.all([loadLogs(), loadReviewList(), loadDocumentHistory()]);
    } else {
      autoReviewBlockedSignatures.set(poNo, context.autoReviewSignature);
      await Promise.all([loadLogs(), loadReviewList()]);
    }
    return result;
  } catch (error) {
    console.warn('Backend auto review failed:', error);
    return null;
  }
}

async function loadPreviewFile(key, endpoint, fallbackUrl) {
  previewState.value[key] = { ...previewState.value[key], loading: true };
  try {
    const response = await apiFetch(endpoint);
    if (!response.ok) throw new Error(await response.text());
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    objectUrls.add(url);
    previewState.value[key] = { url, type: blob.type, loading: false };
  } catch (error) {
    console.warn(`Failed to load ${key} preview:`, error);
    previewState.value[key] = { url: fallbackUrl, type: contentTypeFromUrl(fallbackUrl), loading: false };
  }
}

async function openPurchaseOrderPreview(poNo) {
  if (!poNo) return;
  closePurchaseOrderPreview();
  poPreview.value = { show: true, poNo, url: '', type: '', loading: true, error: '' };
  try {
    const response = await apiFetch(`/finance/purchase-orders/${encodeURIComponent(poNo)}/file`);
    if (!response.ok) throw new Error(await response.text());
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    objectUrls.add(url);
    poPreview.value = { show: true, poNo, url, type: blob.type, loading: false, error: '' };
  } catch (error) {
    console.warn('Failed to load purchase order preview:', error);
    poPreview.value = {
      show: true,
      poNo,
      url: '',
      type: '',
      loading: false,
      error: t('finance.match.load_po_file_failed', { message: error.message }),
    };
  }
}

function closePurchaseOrderPreview() {
  if (poPreview.value.url) {
    URL.revokeObjectURL(poPreview.value.url);
    objectUrls.delete(poPreview.value.url);
  }
  poPreview.value = { show: false, poNo: '', url: '', type: '', loading: false, error: '' };
}

function revokePreviewUrls() {
  objectUrls.forEach(url => URL.revokeObjectURL(url));
  objectUrls.clear();
}

async function submitDecision(decision) {
  if (!activePoNo.value) return;
  decisionBusy.value = true;
  try {
    const endpoint = decision === 'approve'
      ? `/finance/match-groups/${encodeURIComponent(activePoNo.value)}/auto-review`
      : `/finance/match-groups/${encodeURIComponent(activePoNo.value)}/hold`;
    const response = await apiFetch(endpoint, { method: 'POST' });
    if (!response.ok) throw new Error(await response.text());
    updateLocalGroupStatus(activePoNo.value, decision === 'approve' ? 'approved' : 'onHold');
    await loadLogs();
    closeDetail();
  } catch (error) {
    detailError.value = t('finance.match.action_failed', { message: error.message });
  } finally {
    decisionBusy.value = false;
  }
}

async function approvePurchaseOrder(poNo) {
  if (!poNo) return;
  decisionBusy.value = true;
  poListError.value = '';
  try {
    const response = await apiFetch(`/finance/purchase-orders/${encodeURIComponent(poNo)}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actionType: 1 }),
    });
    if (!response.ok) throw new Error(await response.text());
    pendingPurchaseOrders.value = pendingPurchaseOrders.value.filter(row => row.poNo !== poNo);
    await loadReviewList();
    await loadLogs();
  } catch (error) {
    console.error('Approve purchase order failed:', error);
    poListError.value = t('finance.match.po_approve_failed', { message: error.message });
  } finally {
    decisionBusy.value = false;
  }
}

function openPoRejectModal(poNo) {
  poRejectNo.value = poNo;
  poRejectReason.value = '';
  showPoRejectModal.value = true;
}

async function confirmRejectPurchaseOrder() {
  if (!poRejectNo.value || !poRejectReason.value.trim()) return;
  decisionBusy.value = true;
  poListError.value = '';
  try {
    const poNo = poRejectNo.value;
    const response = await apiFetch(`/finance/purchase-orders/${encodeURIComponent(poRejectNo.value)}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actionType: 2, rejectReason: poRejectReason.value.trim() }),
    });
    if (!response.ok) throw new Error(await response.text());
    pendingPurchaseOrders.value = pendingPurchaseOrders.value.filter(row => row.poNo !== poNo);
    showPoRejectModal.value = false;
    poRejectNo.value = '';
    poRejectReason.value = '';
    decisionBusy.value = false;
    refreshReviewQueue({ silent: true });
  } catch (error) {
    console.error('Reject purchase order failed:', error);
    poListError.value = t('finance.match.po_reject_failed', { message: error.message });
    decisionBusy.value = false;
  }
}

async function voidGroup(poNo) {
  if (!poNo) return;
  const confirmed = window.confirm(t('finance.match.void_group_confirm', { poNo }));
  if (!confirmed) return;
  decisionBusy.value = true;
  listError.value = '';
  try {
    const response = await apiFetch(`/finance/match-groups/${encodeURIComponent(poNo)}/void`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: t('finance.match.void_group_default_reason') }),
    });
    if (!response.ok) throw new Error(await response.text());
    updateLocalGroupStatus(poNo, 'void');
    decisionBusy.value = false;
    refreshReviewQueue({ silent: true });
  } catch (error) {
    console.error('Void match group failed:', error);
    listError.value = t('finance.match.void_group_failed', { message: error.message });
    decisionBusy.value = false;
  }
}

async function confirmReject() {
  if (!activePoNo.value || !rejectReason.value.trim()) return;
  decisionBusy.value = true;
  try {
    const poNo = activePoNo.value;
    const response = await apiFetch(`/finance/match-groups/${encodeURIComponent(activePoNo.value)}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        docType: rejectDocType.value,
        rejectReason: rejectReason.value.trim(),
      }),
    });
    if (!response.ok) throw new Error(await response.text());
    updateLocalGroupStatus(poNo, 'onHold');
    showRejectModal.value = false;
    rejectReason.value = '';
    closeDetail();
    decisionBusy.value = false;
    refreshReviewQueue({ silent: true });
  } catch (error) {
    detailError.value = t('finance.match.reject_failed', { message: error.message });
    decisionBusy.value = false;
  }
}

function updateLocalGroupStatus(poNo, groupStatus) {
  reviewRows.value = reviewRows.value.map(row => {
    const rowPoNo = row.poNo || row.po_no;
    return rowPoNo === poNo ? { ...row, groupStatus } : row;
  });
}

function documentTypeLabel(docType) {
  if (docType === 'purchaseOrder') return t('finance.match.purchase_order');
  if (docType === 'goodsReceipt') return t('finance.match.goods_receipt');
  if (docType === 'invoice') return t('finance.match.invoice');
  if (docType === 'matchGroup') return t('finance.match.match_group');
  return docType || '-';
}

function formatDateTime(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('zh-TW', {
    timeZone: 'Asia/Singapore',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date).replace(/\//g, '-');
}

function numberValue(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatCurrency(value) {
  return `$${numberValue(value).toLocaleString('zh-TW', { maximumFractionDigits: 0 })}`;
}

function contentTypeFromUrl(url) {
  if (url.endsWith('.svg')) return 'image/svg+xml';
  if (url.endsWith('.png')) return 'image/png';
  if (url.endsWith('.jpg') || url.endsWith('.jpeg')) return 'image/jpeg';
  return 'application/pdf';
}
</script>

<style scoped>
.finance-page {
  min-height: 100vh;
  background: #f6f7f9;
  color: #111827;
  padding: 28px;
}

.review-shell,
.workbench {
  max-width: 1440px;
  margin: 0 auto;
}

.top-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid #d8dee8;
  margin-bottom: 20px;
}

.tab-btn,
.summary-tile,
.primary-btn,
.secondary-btn,
.approve-btn,
.hold-btn,
.reject-btn,
.back-btn {
  border: 0;
  cursor: pointer;
  font: inherit;
}

.tab-btn {
  background: transparent;
  color: #5f6b7a;
  padding: 11px 18px;
  border-bottom: 3px solid transparent;
  font-weight: 700;
}

.tab-active {
  color: #1f5eff;
  border-bottom-color: #1f5eff;
}

.page-header,
.workbench-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.page-header h1,
.workbench-header h1 {
  margin: 0;
  font-size: 24px;
  line-height: 1.25;
}

.page-header p,
.workbench-header p {
  margin: 6px 0 0;
  color: #5f6b7a;
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.list-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.list-toolbar label {
  font-weight: 800;
  color: #334155;
}

.list-toolbar select {
  width: min(420px, 100%);
  min-height: 44px;
  font-size: 14px;
  line-height: 1.35;
  background: #fff;
}

.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.summary-tile {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border: 1px solid #d8dee8;
  border-radius: 8px;
  padding: 14px 16px;
  text-align: left;
}

.summary-tile.active {
  border-color: #1f5eff;
  box-shadow: inset 0 0 0 1px #1f5eff;
}

.summary-tile span {
  color: #5f6b7a;
}

.summary-tile strong {
  font-size: 24px;
}

.table-wrap {
  overflow-x: auto;
  background: #fff;
  border: 1px solid #d8dee8;
  border-radius: 8px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  border-bottom: 1px solid #e3e7ee;
  padding: 12px 14px;
  text-align: left;
  vertical-align: top;
  font-size: 14px;
}

.data-table th {
  background: #eef3ff;
  font-weight: 800;
}

.data-table tr:last-child td {
  border-bottom: 0;
}

.data-table tr.priority td:first-child {
  border-left: 4px solid #16a34a;
}

.key-cell {
  font-weight: 800;
}

.doc-pill,
.status-badge {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 800;
}

.doc-pill.present,
.status-badge.complete,
.status-badge.ok {
  background: #dcfce7;
  color: #166534;
}

.doc-pill.missing,
.status-badge.waiting {
  background: #fef3c7;
  color: #92400e;
}

.status-badge.onHold,
.status-badge.tolerance {
  background: #ffedd5;
  color: #9a3412;
}

.status-badge.mismatch {
  background: #fee2e2;
  color: #991b1b;
}

.primary-btn,
.secondary-btn,
.approve-btn,
.hold-btn,
.reject-btn,
.back-btn {
  min-height: 38px;
  border-radius: 7px;
  padding: 0 15px;
  font-weight: 800;
}

.primary-btn,
.approve-btn {
  background: #16a34a;
  color: #fff;
}

.secondary-btn,
.back-btn {
  background: #fff;
  color: #334155;
  border: 1px solid #9ca3af;
}

.hold-btn {
  background: #f97316;
  color: #fff;
}

.reject-btn {
  background: #dc3545;
  color: #fff;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.sm {
  min-height: 30px;
  padding: 0 10px;
  font-size: 13px;
}

.empty-cell,
.empty-box,
.empty-preview {
  color: #64748b;
  text-align: center;
  padding: 34px 18px;
}

.section-heading {
  margin: 20px 0 12px;
  font-size: 18px;
}

.empty-box {
  background: #fff;
  border: 1px solid #d8dee8;
  border-radius: 8px;
}

.empty-box.error {
  color: #991b1b;
  border-color: #fecaca;
  background: #fef2f2;
}

.workbench-header {
  border-bottom: 1px solid #d8dee8;
  padding-bottom: 18px;
}

.workbench-actions {
  display: flex;
  gap: 10px;
}

.workbench-body {
  display: grid;
  grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
  gap: 22px;
  align-items: start;
}

.preview-panel {
  position: sticky;
  top: 18px;
}

.doc-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  background: #fff;
  border-bottom: 1px solid #d8dee8;
}

.doc-tab {
  background: #fff;
  border: 0;
  border-bottom: 3px solid transparent;
  padding: 13px 8px;
  color: #64748b;
  font-weight: 800;
  cursor: pointer;
}

.doc-tab.active {
  color: #1f5eff;
  border-bottom-color: #1f5eff;
}

.preview-frame {
  background: #fff;
  border: 1px solid #d8dee8;
  border-radius: 8px;
  overflow: hidden;
}

.preview-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 13px;
  border-bottom: 1px solid #d8dee8;
}

.preview-toolbar a {
  color: #1f5eff;
  font-size: 13px;
  text-decoration: none;
}

.file-object {
  display: block;
  width: 100%;
  height: 620px;
  background: #fff;
}

.file-image {
  display: block;
  max-width: 100%;
}

.compare-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.review-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.review-meta > div,
.totals-box,
.compare-section {
  background: #fff;
  border: 1px solid #d8dee8;
  border-radius: 8px;
}

.review-meta > div {
  padding: 12px 14px;
}

.review-meta span {
  display: block;
  color: #64748b;
  font-size: 13px;
  margin-bottom: 4px;
}

.match-result-box {
  background: #fff;
  border: 1px solid #d8dee8;
  border-radius: 8px;
  padding: 14px 16px;
}

.match-result-box.ok {
  border-color: #86efac;
  background: #f0fdf4;
}

.match-result-box.mismatch {
  border-color: #fecaca;
  background: #fef2f2;
}

.match-result-box.waiting {
  border-color: #fde68a;
  background: #fffbeb;
}

.match-result-box span {
  display: block;
  color: #64748b;
  font-size: 13px;
  margin-bottom: 4px;
}

.match-result-box strong {
  font-size: 18px;
}

.match-result-box p {
  margin: 8px 0 0;
  color: #475569;
}

.compare-section {
  overflow-x: auto;
}

.compare-section h2 {
  margin: 0;
  padding: 15px 16px 0;
  font-size: 18px;
}

.compare-table {
  margin-top: 12px;
}

.line-values {
  display: grid;
  gap: 6px;
}

.line-values div {
  display: flex;
  gap: 10px;
}

.line-values span {
  min-width: 34px;
  color: #64748b;
  font-size: 13px;
}

.issue-text {
  margin: 6px 0 0;
  color: #991b1b;
  font-size: 13px;
  line-height: 1.35;
}

.totals-box {
  padding: 15px 20px;
}

.totals-box div {
  display: flex;
  justify-content: space-between;
  padding: 7px 0;
}

.totals-box .grand {
  border-top: 1px solid #d8dee8;
  margin-top: 4px;
  padding-top: 12px;
  font-size: 17px;
}

textarea,
select {
  width: 100%;
  border: 1px solid #9ca3af;
  border-radius: 7px;
  padding: 10px 11px;
  font: inherit;
  box-sizing: border-box;
}

select {
  min-height: 42px;
  height: auto;
  font-size: 14px;
  line-height: 1.35;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.45);
}

.modal-box {
  width: min(520px, calc(100vw - 32px));
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 18px 60px rgba(15, 23, 42, 0.22);
}

.preview-modal {
  width: min(960px, calc(100vw - 32px));
  max-height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
}

.preview-modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.modal-preview-toolbar {
  margin-top: 12px;
}

.po-preview-frame {
  min-height: 68vh;
  margin-top: 0;
}

.modal-box h2 {
  margin: 0 0 5px;
}

.modal-box p {
  margin: 0 0 18px;
  color: #64748b;
}

.modal-box textarea,
.modal-box select {
  margin-bottom: 16px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 980px) {
  .finance-page {
    padding: 16px;
  }

  .summary-strip,
  .review-meta,
  .workbench-body {
    grid-template-columns: 1fr;
  }

  .preview-panel {
    position: static;
  }

  .page-header,
  .workbench-header {
    align-items: stretch;
    flex-direction: column;
  }

  .workbench-actions {
    width: 100%;
  }

  .workbench-actions button {
    flex: 1;
  }
}
</style>
