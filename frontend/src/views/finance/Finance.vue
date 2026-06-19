<template>
  <div class="system-container">

    <!-- ===== 主頁（清單 or Log）===== -->
    <div v-if="!activeInvoice" class="system-block">

      <!-- 頁面切換 Tabs -->
      <div class="top-tabs">
        <button :class="['tab-btn', activeTab === 'review' ? 'tab-active' : '']" @click="activeTab = 'review'">
          {{ $t('finance.tab_review') }}
        </button>
        <button :class="['tab-btn', activeTab === 'log' ? 'tab-active' : '']" @click="activeTab = 'log'">
          {{ $t('finance.tab_log') }}
        </button>
      </div>

      <!-- ===== 審核頁 ===== -->
      <div v-if="activeTab === 'review'">
        <div class="page-header">
          <h1 class="page-title">{{ $t('finance.invoice_matching_title') }}</h1>
          <div class="header-actions">
            <button @click="batchApprove" class="dashboard-btn approve-btn" :disabled="selectedIds.length === 0">
              {{ $t('finance.batch_approve') }} ({{ selectedIds.length }})
            </button>
          </div>
        </div>

        <!-- 統計卡片 -->
        <div class="stats-bar">
          <div class="stat-card" :class="{ 'stat-active': filterStatus === '' }" @click="filterStatus = ''" style="cursor:pointer">
            <span class="stat-label">{{ $t('finance.filter_all') }}</span>
            <span class="stat-count">{{ invoices.length }}</span>
          </div>
          <div class="stat-card" :class="{ 'stat-active': filterStatus === 'matched' }" @click="filterStatus = filterStatus === 'matched' ? '' : 'matched'" style="cursor:pointer">
            <span class="stat-label">{{ $t('finance.status_matched') }}</span>
            <span class="stat-count">{{ countByStatus('matched') }}</span>
          </div>
          <div class="stat-card" :class="{ 'stat-active': filterStatus === 'low_confidence' }" @click="filterStatus = filterStatus === 'low_confidence' ? '' : 'low_confidence'" style="cursor:pointer">
            <span class="stat-label">{{ $t('finance.status_low_confidence') }}</span>
            <span class="stat-count">{{ countByStatus('low_confidence') }}</span>
          </div>
          <div class="stat-card" :class="{ 'stat-active': filterStatus === 'mismatch' }" @click="filterStatus = filterStatus === 'mismatch' ? '' : 'mismatch'" style="cursor:pointer">
            <span class="stat-label">{{ $t('finance.status_mismatch') }}</span>
            <span class="stat-count">{{ countByStatus('mismatch') }}</span>
          </div>
        </div>

        <!-- Filter 工具列 -->
        <div class="filter-bar">
          <span class="filter-label">{{ $t('finance.filter_status') }}：</span>
          <select v-model="filterStatus" class="filter-select">
            <option value="">{{ $t('finance.filter_all') }}</option>
            <option value="matched">{{ $t('finance.status_matched') }}</option>
            <option value="low_confidence">{{ $t('finance.status_low_confidence') }}</option>
            <option value="mismatch">{{ $t('finance.status_mismatch') }}</option>
          </select>
          <span class="filter-result">{{ $t('finance.filter_showing') }} {{ filteredInvoices.length }} {{ $t('finance.filter_items') }}</span>
        </div>

        <!-- 發票清單表格 -->
        <div class="table-container">
          <table class="records-table">
            <thead>
              <tr>
                <th><input type="checkbox" @change="toggleSelectAll" /></th>
                <th>{{ $t('finance.col_invoice_no') }}</th>
                <th>{{ $t('finance.col_po_no') }}</th>
                <th>{{ $t('finance.col_vendor') }}</th>
                <th>{{ $t('finance.col_invoice_date') }}</th>
                <th>{{ $t('finance.col_amount') }}</th>
                <th>{{ $t('finance.col_status') }}</th>
                <th>{{ $t('finance.col_actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="inv in filteredInvoices" :key="inv.invoiceNo" :class="'row-' + inv.status">
                <td><input type="checkbox" v-model="selectedIds" :value="inv.invoiceNo" :disabled="inv.status !== 'matched'" /></td>
                <td>{{ inv.invoiceNo }}</td>
                <td>{{ inv.poNo }}</td>
                <td>{{ inv.vendor }}</td>
                <td>{{ inv.invoiceDate }}</td>
                <td>{{ formatCurrency(inv.invoiceTotal) }}</td>
                <td>
                  <span :class="'badge badge-' + inv.status">
                    {{ statusIcon(inv.status) }} {{ $t('finance.status_' + inv.status) }}
                  </span>
                </td>
                <td>
                  <button v-if="inv.status === 'matched'" @click="approveInvoice(inv.invoiceNo)" class="dashboard-btn approve-btn sm-btn">
                    {{ $t('finance.approve') }}
                  </button>
                  <button @click="openDetail(inv)" class="dashboard-btn review-btn sm-btn">
                    {{ $t('finance.review') }}
                  </button>
                </td>
              </tr>
              <tr v-if="filteredInvoices.length === 0">
                <td colspan="8" style="text-align:center; color:#999; padding: 2rem;">{{ $t('finance.no_records') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ===== 操作紀錄 Log 頁 ===== -->
      <div v-else class="log-page">
        <div class="page-header">
          <h1 class="page-title">{{ $t('finance.tab_log') }}</h1>
          <button @click="globalAuditLog = []" class="dashboard-btn reject-btn sm-btn">{{ $t('finance.log_clear') }}</button>
        </div>

        <div v-if="globalAuditLog.length === 0" class="log-empty">
          {{ $t('finance.log_empty') }}
        </div>
        <div v-else class="table-container">
          <table class="records-table">
            <thead>
              <tr>
                <th>{{ $t('finance.log_col_time') }}</th>
                <th>{{ $t('finance.log_col_invoice') }}</th>
                <th>{{ $t('finance.log_col_action') }}</th>
                <th>{{ $t('finance.log_col_remark') }}</th>
                <th>{{ $t('finance.log_col_detail') }}</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="(entry, i) in globalAuditLog" :key="i">
                <tr :class="'log-row-' + entry.type">
                  <td class="log-time">{{ entry.time }}</td>
                  <td>{{ entry.invoiceNo }}</td>
                  <td>
                    <span :class="'badge badge-log-' + entry.type">{{ entry.actionLabel }}</span>
                  </td>
                  <td>{{ entry.remark || '—' }}</td>
                  <td class="log-detail-cell">
                    <button
                      v-if="entry.snapshot"
                      class="detail-toggle-btn"
                      @click="expandedLogIndex = expandedLogIndex === i ? null : i"
                    >
                      {{ expandedLogIndex === i ? '▲ ' + $t('finance.log_collapse') : '▼ ' + $t('finance.log_expand') }}
                    </button>
                    <span v-else>—</span>
                  </td>
                </tr>
                <!-- 展開的細項列 -->
                <tr v-if="expandedLogIndex === i && entry.snapshot" class="log-detail-row">
                  <td :colspan="5">
                    <div class="log-snapshot">
                      <div class="snapshot-header">
                        <span><strong>{{ entry.invoiceNo }}</strong> / {{ entry.snapshot.poNo }} — {{ entry.snapshot.vendor }}</span>
                      </div>
                      <table class="snapshot-table">
                        <thead>
                          <tr>
                            <th>{{ $t('finance.item_name') }}</th>
                            <th>PO {{ $t('finance.qty') }}</th>
                            <th>PO {{ $t('finance.unit_price') }}</th>
                            <th>Invoice {{ $t('finance.qty') }}</th>
                            <th>Invoice {{ $t('finance.unit_price') }}</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(line, li) in entry.snapshot.lines" :key="li">
                            <td>{{ line.itemName }}</td>
                            <td>{{ line.poQty }}</td>
                            <td>{{ formatCurrency(line.poUnitPrice) }}</td>
                            <td :class="{ 'changed-val': entry.snapshot.origLines && entry.snapshot.origLines[li] && line.invQty !== entry.snapshot.origLines[li].invQty }">
                              {{ line.invQty }}
                              <span v-if="entry.snapshot.origLines && entry.snapshot.origLines[li] && line.invQty !== entry.snapshot.origLines[li].invQty" class="orig-val">
                                ({{ $t('finance.log_was') }} {{ entry.snapshot.origLines[li].invQty }})
                              </span>
                            </td>
                            <td :class="{ 'changed-val': entry.snapshot.origLines && entry.snapshot.origLines[li] && line.invUnitPrice !== entry.snapshot.origLines[li].invUnitPrice }">
                              {{ formatCurrency(line.invUnitPrice) }}
                              <span v-if="entry.snapshot.origLines && entry.snapshot.origLines[li] && line.invUnitPrice !== entry.snapshot.origLines[li].invUnitPrice" class="orig-val">
                                ({{ $t('finance.log_was') }} {{ formatCurrency(entry.snapshot.origLines[li].invUnitPrice) }})
                              </span>
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ===== 逐筆對照工作台 ===== -->
    <div v-else class="workbench">
      <div class="workbench-header">
        <button @click="closeDetail" class="back-btn">← {{ $t('finance.back_to_list') }}</button>
        <h2>{{ $t('finance.detail_title') }} — {{ activeInvoice.invoiceNo }} / {{ activeInvoice.poNo }}</h2>
        <div class="workbench-actions">
          <button @click="submitDecision('approve')" class="dashboard-btn approve-btn">{{ $t('finance.approve') }}</button>
          <button @click="submitDecision('hold')" class="dashboard-btn hold-btn">{{ $t('finance.hold') }}</button>
          <button @click="showRejectModal = true" class="dashboard-btn reject-btn">{{ $t('finance.reject') }}</button>
        </div>
      </div>

      <div class="workbench-body">
        <!-- 左側：發票影像 -->
        <div class="invoice-image-panel">
          <h3>{{ $t('finance.panel_invoice_image') }}</h3>
          <div class="image-wrapper">
            <img :src="activeInvoice.imageUrl" alt="Invoice" class="invoice-img" />
          </div>
        </div>

        <!-- 右側 -->
        <div class="right-panel">
          <!-- 三方摘要表格 -->
          <div class="summary-section">
            <h3>{{ $t('finance.panel_summary') }}</h3>
            <table class="records-table summary-table">
              <thead>
                <tr>
                  <th>{{ $t('finance.item_name') }}</th>
                  <th>{{ $t('finance.col_po') }}</th>
                  <th>{{ $t('finance.col_gr') }}</th>
                  <th>{{ $t('finance.col_invoice') }}</th>
                  <th>{{ $t('finance.col_status') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(line, idx) in editableLines" :key="idx">
                  <td>{{ line.itemName }}</td>
                  <!-- PO 欄 -->
                  <td>
                    <div class="cell-pair">
                      <span class="cell-label">{{ $t('finance.qty') }}</span>
                      <span>{{ line.poQty }}</span>
                    </div>
                    <div class="cell-pair">
                      <span class="cell-label">{{ $t('finance.unit_price') }}</span>
                      <span>{{ formatCurrency(line.poUnitPrice) }}</span>
                    </div>
                  </td>
                  <!-- GR 欄 -->
                  <td>
                    <div class="cell-pair">
                      <span class="cell-label">{{ $t('finance.qty') }}</span>
                      <span>{{ line.grQty }}</span>
                    </div>
                    <div class="cell-pair">
                      <span class="cell-label">{{ $t('finance.unit_price') }}</span>
                      <span>{{ formatCurrency(line.grUnitPrice) }}</span>
                    </div>
                  </td>
                  <!-- Invoice 欄（可編輯） -->
                  <td>
                    <div class="cell-pair">
                      <span class="cell-label">{{ $t('finance.qty') }}</span>
                      <span>{{ line.invQty }}</span>
                    </div>
                    <div class="cell-pair">
                      <span class="cell-label">{{ $t('finance.unit_price') }}</span>
                      <span>{{ formatCurrency(line.invUnitPrice) }}</span>
                    </div>
                  </td>
                  <!-- 行狀態 -->
                  <td>
                    <span v-if="lineStatus(line) === 'ok'" class="badge badge-matched">{{ $t('finance.line_ok') }}</span>
                    <span v-else-if="lineStatus(line) === 'tolerance'" class="badge badge-low-confidence">{{ $t('finance.line_tolerance') }}</span>
                    <span v-else class="badge badge-mismatch">{{ $t('finance.line_mismatch') }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 稅額與總計 -->
          <div class="totals-section">
            <div class="total-row">
              <span>{{ $t('finance.subtotal') }}</span>
              <span>{{ formatCurrency(computedSubtotal) }}</span>
            </div>
            <div class="total-row">
              <span>{{ $t('finance.tax') }} ({{ (TAX_RATE * 100).toFixed(0) }}%)</span>
              <span>{{ formatCurrency(computedTax) }}</span>
            </div>
            <div class="total-row grand-total">
              <span>{{ $t('finance.total') }}</span>
              <span>{{ formatCurrency(computedTotal) }}</span>
            </div>
            <div v-if="toleranceHint" class="tolerance-hint">{{ $t('finance.tolerance_hint') }}</div>
          </div>

          <!-- 異常標註與操作區 -->
          <div class="edit-section">
            <label class="edit-label">{{ $t('finance.anomaly_remark') }}</label>
            <textarea v-model="anomalyRemark" class="anomaly-textarea" rows="3" :placeholder="$t('finance.anomaly_placeholder')"></textarea>
          </div>

          <!-- Audit Trail 顯示 -->
          <div v-if="auditTrail.length" class="audit-section">
            <h4>{{ $t('finance.audit_trail') }}</h4>
            <ul class="audit-list">
              <li v-for="(entry, i) in auditTrail" :key="i" class="audit-entry">
                <span class="audit-time">{{ entry.time }}</span>
                {{ $t('finance.audit_changed') }}
                <strong>{{ entry.field }}</strong>
                {{ $t('finance.audit_from') }} <code>{{ entry.oldVal }}</code>
                {{ $t('finance.audit_to') }} <code>{{ entry.newVal }}</code>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 退回原因 Modal ===== -->
    <transition name="fade">
      <div v-if="showRejectModal" class="modal-overlay" @click.self="showRejectModal = false">
        <div class="modal-box">
          <h3 class="modal-title">{{ $t('finance.reject_modal_title') }}</h3>
          <p class="modal-sub">{{ activeInvoice?.invoiceNo }} / {{ activeInvoice?.poNo }}</p>
          <label class="edit-label">{{ $t('finance.reject_reason_label') }}<span class="required">*</span></label>
          <textarea
            v-model="rejectReason"
            class="anomaly-textarea"
            rows="4"
            :placeholder="$t('finance.reject_reason_placeholder')"
            autofocus
          ></textarea>
          <div class="modal-actions">
            <button @click="showRejectModal = false" class="dashboard-btn back-modal-btn">{{ $t('finance.cancel') }}</button>
            <button @click="confirmReject" class="dashboard-btn reject-btn" :disabled="!rejectReason.trim()">{{ $t('finance.reject_confirm') }}</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { apiFetch } from '@/api.js';

const { t } = useI18n();
const TAX_RATE = 0.05;

// ── 動態容忍比率（由管理員設定） ──
const toleranceRate = ref(0.01); // fallback default

onMounted(async () => {
  try {
    const res = await apiFetch('/admin/system-settings');
    if (res.ok) {
      const settings = await res.json();
      const found = settings.find(s => s.key === 'tolerance_rate');
      if (found) toleranceRate.value = Number(found.value);
    }
  } catch (e) {
    console.warn('Failed to fetch tolerance_rate, using default:', e);
  }
});

// ── 頁面 Tab ──
const activeTab = ref('review');  // 'review' | 'log'

// ── Mock 發票資料 ──
const invoices = ref([
  {
    invoiceNo: 'INV-2026-001',
    poNo: 'PO-8801',
    vendor: '科技供應商 A',
    invoiceDate: '2026-03-20',
    invoiceTotal: 625000,
    status: 'matched',
    imageUrl: '/invoices/INV-2026-001.svg',
    lines: [
      { itemName: 'MacBook Pro', poQty: 10, poUnitPrice: 60000, grQty: 10, grUnitPrice: 60000, invQty: 10, invUnitPrice: 60000, ocrBox: { top: 28, left: 5, width: 55, height: 7 }, ocrBoxUnitPrice: { top: 36, left: 5, width: 55, height: 7 } },
      { itemName: 'Magic Mouse', poQty: 10, poUnitPrice: 2500, grQty: 10, grUnitPrice: 2500, invQty: 10, invUnitPrice: 2500, ocrBox: { top: 37, left: 5, width: 55, height: 7 }, ocrBoxUnitPrice: { top: 45, left: 5, width: 55, height: 7 } },
    ],
  },
  {
    invoiceNo: 'INV-2026-002',
    poNo: 'PO-8802',
    vendor: '辦公設備 B',
    invoiceDate: '2026-03-21',
    invoiceTotal: 66500,
    status: 'low_confidence',
    imageUrl: '/invoices/INV-2026-002.svg',
    lines: [
      { itemName: 'Dell 顯示器 U2724D', poQty: 5, poUnitPrice: 12000, grQty: 5, grUnitPrice: 12000, invQty: 5, invUnitPrice: 12100, ocrBox: { top: 28, left: 5, width: 55, height: 7 }, ocrBoxUnitPrice: { top: 36, left: 5, width: 55, height: 7 } },
      { itemName: 'Dell 顯示器支架 MDA20', poQty: 5, poUnitPrice: 1200, grQty: 5, grUnitPrice: 1200, invQty: 5, invUnitPrice: 1200, ocrBox: { top: 37, left: 5, width: 55, height: 7 }, ocrBoxUnitPrice: { top: 45, left: 5, width: 55, height: 7 } },
    ],
  },
  {
    invoiceNo: 'INV-2026-003',
    poNo: 'PO-8803',
    vendor: '耗材供應商 C',
    invoiceDate: '2026-03-22',
    invoiceTotal: 40800,
    status: 'mismatch',
    imageUrl: '/invoices/INV-2026-003.svg',
    lines: [
      { itemName: 'A4 影印紙（箱）', poQty: 30, poUnitPrice: 800, grQty: 30, grUnitPrice: 800, invQty: 33, invUnitPrice: 1100, ocrBox: { top: 28, left: 5, width: 55, height: 7 }, ocrBoxUnitPrice: { top: 36, left: 5, width: 55, height: 7 } },
      { itemName: '訂書機 HD-50', poQty: 10, poUnitPrice: 450, grQty: 10, grUnitPrice: 450, invQty: 10, invUnitPrice: 450, ocrBox: { top: 37, left: 5, width: 55, height: 7 }, ocrBoxUnitPrice: { top: 45, left: 5, width: 55, height: 7 } },
    ],
  },
]);

// ── Filter ──
const filterStatus = ref('');

const filteredInvoices = computed(() =>
  filterStatus.value ? invoices.value.filter(i => i.status === filterStatus.value) : invoices.value
);

const selectedIds = ref([]);
const activeInvoice = ref(null);
const expandedLogIndex = ref(null);
const editableLines = ref([]);
const anomalyRemark = ref('');
const auditTrail = ref([]);
const globalAuditLog = ref([]);
const highlightBox = ref(null);
const showRejectModal = ref(false);
const rejectReason = ref('');

// ── 統計 ──
const matchedCount = computed(() => invoices.value.filter(i => i.status === 'matched').length);

function countByStatus(status) {
  return invoices.value.filter(i => i.status === status).length;
}

function statusIcon(status) {
  return '';
}

// ── 格式化 ──
function formatCurrency(val) {
  return `$${Number(val).toLocaleString('zh-TW')}`;
}

function nowTime() {
  return new Date().toLocaleString('zh-TW', { hour12: false });
}

// ── 清單操作 ──
function toggleSelectAll(e) {
  selectedIds.value = e.target.checked
    ? filteredInvoices.value.filter(i => i.status === 'matched').map(i => i.invoiceNo)
    : [];
}

function approveInvoice(invoiceNo) {
  const inv = invoices.value.find(i => i.invoiceNo === invoiceNo);
  globalAuditLog.value.unshift({
    time: nowTime(), invoiceNo, actionLabel: t('finance.log_action_approve'), type: 'approve',
    field: undefined, oldVal: undefined, newVal: undefined,
    snapshot: inv ? { poNo: inv.poNo, vendor: inv.vendor, lines: inv.lines.map(l => ({ ...l })) } : undefined,
  });
  invoices.value = invoices.value.filter(i => i.invoiceNo !== invoiceNo);
  selectedIds.value = selectedIds.value.filter(id => id !== invoiceNo);
}

function batchApprove() {
  const ids = [...selectedIds.value];
  ids.forEach(id => {
    const inv = invoices.value.find(i => i.invoiceNo === id);
    globalAuditLog.value.unshift({
      time: nowTime(), invoiceNo: id, actionLabel: t('finance.log_action_batch_approve'), type: 'approve',
      field: undefined, oldVal: undefined, newVal: undefined,
      snapshot: inv ? { poNo: inv.poNo, vendor: inv.vendor, lines: inv.lines.map(l => ({ ...l })) } : undefined,
    });
  });
  invoices.value = invoices.value.filter(i => !ids.includes(i.invoiceNo));
  selectedIds.value = [];
}

// ── 詳細工作台 ──
function openDetail(inv) {
  activeInvoice.value = inv;
  editableLines.value = inv.lines.map(l => ({ ...l }));
  anomalyRemark.value = '';
  auditTrail.value = [];
  highlightBox.value = null;
  globalAuditLog.value.unshift({
    time: nowTime(), invoiceNo: inv.invoiceNo, actionLabel: t('finance.log_action_open'), type: 'info',
    field: undefined, oldVal: undefined, newVal: undefined,
  });
}

function closeDetail() {
  activeInvoice.value = null;
}

function highlightField(line, field) {
  highlightBox.value = field === 'qty' ? line.ocrBox : line.ocrBoxUnitPrice;
}

function recordAudit(line, field, event) {
  const newVal = event.target.value;
  const fieldLabel = field === 'invQty' ? t('finance.qty') : t('finance.unit_price');
  const oldVal = field === 'invQty' ? (line._prevQty ?? line.invQty) : (line._prevPrice ?? line.invUnitPrice);
  if (String(oldVal) === String(newVal)) return;
  const entry = {
    time: nowTime(),
    field: `${line.itemName} — ${fieldLabel}`,
    oldVal,
    newVal,
  };
  auditTrail.value.push(entry);
  globalAuditLog.value.unshift({
    ...entry,
    invoiceNo: activeInvoice.value?.invoiceNo ?? '',
    actionLabel: t('finance.log_action_edit'),
    type: 'edit',
  });
}

// 行狀態（容差由管理員設定）
function lineStatus(line) {
  const qtyOk = line.invQty === line.poQty && line.invQty === line.grQty;
  const priceDiff = Math.abs(line.invUnitPrice - line.poUnitPrice);
  const priceTolerance = line.poUnitPrice * toleranceRate.value;
  if (!qtyOk || priceDiff > priceTolerance) return 'mismatch';
  if (priceDiff > 0 && priceDiff <= priceTolerance) return 'tolerance';
  return 'ok';
}

// 計算小計、稅額、總計
const computedSubtotal = computed(() =>
  editableLines.value.reduce((sum, l) => sum + l.invQty * l.invUnitPrice, 0)
);
const computedTax = computed(() => computedSubtotal.value * TAX_RATE);
const computedTotal = computed(() => computedSubtotal.value + computedTax.value);

const toleranceHint = computed(() =>
  editableLines.value.some(l => lineStatus(l) === 'tolerance')
);

// 退回確認（帶原因）
function confirmReject() {
  if (!rejectReason.value.trim()) return;
  globalAuditLog.value.unshift({
    time: nowTime(),
    invoiceNo: activeInvoice.value.invoiceNo,
    actionLabel: t('finance.log_action_reject'),
    type: 'reject',
    field: '—',
    oldVal: undefined,
    newVal: undefined,
    remark: rejectReason.value,
    snapshot: { poNo: activeInvoice.value.poNo, vendor: activeInvoice.value.vendor, lines: activeInvoice.value.lines.map(l => ({ ...l })) },
  });
  invoices.value = invoices.value.filter(i => i.invoiceNo !== activeInvoice.value.invoiceNo);
  showRejectModal.value = false;
  rejectReason.value = '';
  closeDetail();
}

// 審核決策
function submitDecision(decision) {
  const inv = invoices.value.find(i => i.invoiceNo === activeInvoice.value.invoiceNo);
  const actionMap = { approve: t('finance.log_action_approve'), reject: t('finance.log_action_reject'), hold: t('finance.log_action_hold') };
  const typeMap = { approve: 'approve', reject: 'reject', hold: 'hold' };

  // 若 approve 且有改值，自動在 remark 附註變更明細
  let remarkText = anomalyRemark.value || '';
  if (decision === 'approve' && activeInvoice.value) {
    const origLines = activeInvoice.value.lines;
    const changes = [];
    editableLines.value.forEach((edited, idx) => {
      const orig = origLines[idx];
      if (!orig) return;
      if (edited.invQty !== orig.invQty) {
        changes.push(`${orig.itemName} ${t('finance.qty')}: ${orig.invQty} → ${edited.invQty}`);
      }
      if (edited.invUnitPrice !== orig.invUnitPrice) {
        changes.push(`${orig.itemName} ${t('finance.unit_price')}: ${formatCurrency(orig.invUnitPrice)} → ${formatCurrency(edited.invUnitPrice)}`);
      }
    });
    if (changes.length) {
      const changeSummary = changes.join('；');
      remarkText = remarkText ? `${remarkText}\n${changeSummary}` : changeSummary;
    }
  }

  // 存快照（approve / reject 才存）
  const snapshot = (decision === 'approve' || decision === 'reject') && activeInvoice.value
    ? { poNo: activeInvoice.value.poNo, vendor: activeInvoice.value.vendor, lines: editableLines.value.map(l => ({ ...l })), origLines: activeInvoice.value.lines.map(l => ({ ...l })) }
    : undefined;

  globalAuditLog.value.unshift({
    time: nowTime(),
    invoiceNo: activeInvoice.value.invoiceNo,
    actionLabel: actionMap[decision],
    type: typeMap[decision],
    remark: remarkText || undefined,
    snapshot,
  });

  if (decision === 'approve') {
    invoices.value = invoices.value.filter(i => i.invoiceNo !== activeInvoice.value.invoiceNo);
  } else if (decision === 'reject') {
    if (inv) { inv.anomalyRemark = anomalyRemark.value; inv.status = 'mismatch'; }
  } else {
    if (inv) inv.status = 'low_confidence';
  }
  closeDetail();
}
</script>

<style scoped>
/* ===== 基礎 ===== */
.system-container {
  display: flex;
  justify-content: center;
  padding: 2rem;
  font-family: sans-serif;
}

.system-block {
  width: 100%;
  max-width: 1100px;
}

/* ===== Top Tabs ===== */
.top-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #dee2e6;
  padding-bottom: 0;
}

.tab-btn {
  background: none;
  border: none;
  padding: 10px 20px;
  font-size: 1rem;
  cursor: pointer;
  color: #6c757d;
  border-bottom: 3px solid transparent;
  margin-bottom: -2px;
  border-radius: 4px 4px 0 0;
  transition: color 0.15s;
}

.tab-btn:hover { color: #1a3c6e; }

.tab-active {
  color: #1a3c6e !important;
  font-weight: 700;
  border-bottom-color: #1a3c6e !important;
  background: #f0f4ff;
}

/* ===== Filter 工具列 ===== */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  margin-bottom: 1rem;
  padding: 0.6rem 1rem;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
}

.filter-label { font-size: 0.9rem; color: #495057; font-weight: 600; }

.filter-select {
  padding: 5px 10px;
  border: 1px solid #adb5bd;
  border-radius: 6px;
  font-size: 0.9rem;
  background: white;
}

.filter-result {
  margin-left: auto;
  font-size: 0.82rem;
  color: #6c757d;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.2rem;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a1a2e;
}

/* ===== 統計卡片 ===== */
.stats-bar {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.stat-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.9rem 1.2rem;
  border-radius: 10px;
  font-weight: 600;
  background: #f8f9fa;
  border: 2px solid #dee2e6;
  transition: border-color 0.15s, background 0.15s;
}

.stat-card:hover { border-color: #adb5bd; }

.stat-active {
  border-color: #1a3c6e !important;
  background: #e8eeff !important;
}

.stat-card .stat-count {
  margin-left: auto;
  font-size: 1.4rem;
}

/* ===== 表格 ===== */
.table-container { overflow-x: auto; }

.records-table {
  width: 100%;
  border-collapse: collapse;
}

.records-table th,
.records-table td {
  padding: 10px 12px;
  text-align: left;
  border: 1px solid #dee2e6;
  font-size: 0.9rem;
}

.records-table th {
  background-color: #f0f4ff;
  font-weight: 600;
}

.records-table tr:hover { background-color: #f8f9ff; }

/* ===== 狀態行著色 ===== */
.row-matched td:first-child { border-left: 4px solid #28a745; }
.row-low_confidence td:first-child { border-left: 4px solid #ffc107; }
.row-mismatch td:first-child { border-left: 4px solid #dc3545; }

/* ===== 徽章 ===== */
.badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}

.badge-matched { background: #d4edda; color: #155724; }
.badge-low_confidence { background: #fff3cd; color: #856404; }
.badge-mismatch { background: #f8d7da; color: #721c24; }
.badge-low-confidence { background: #fff3cd; color: #856404; }

/* Log 操作徽章 */
.badge-log-approve { background: #d4edda; color: #155724; }
.badge-log-reject  { background: #f8d7da; color: #721c24; }
.badge-log-hold    { background: #ffe5d0; color: #7c3300; }
.badge-log-edit    { background: #cce5ff; color: #004085; }
.badge-log-info    { background: #e2e3e5; color: #383d41; }

/* Log 列著色 */
.log-row-approve td:first-child { border-left: 4px solid #28a745; }
.log-row-reject  td:first-child { border-left: 4px solid #dc3545; }
.log-row-hold    td:first-child { border-left: 4px solid #fd7e14; }
.log-row-edit    td:first-child { border-left: 4px solid #007bff; }
.log-row-info    td:first-child { border-left: 4px solid #adb5bd; }

/* ===== 按鈕 ===== */
.dashboard-btn {
  background-color: #007bff;
  color: white;
  border: none;
  padding: 8px 14px;
  margin: 3px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: filter 0.15s;
}

.dashboard-btn:hover:not(:disabled) { filter: brightness(0.88); }
.dashboard-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.approve-btn { background-color: #28a745; }
.reject-btn  { background-color: #dc3545; }
.hold-btn    { background-color: #fd7e14; }
.review-btn  { background-color: #17a2b8; }

.sm-btn { padding: 4px 10px; font-size: 0.82rem; }

/* ===== Log 頁 ===== */
.log-page { width: 100%; max-width: 1100px; }

.log-empty {
  text-align: center;
  color: #999;
  padding: 3rem;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px dashed #dee2e6;
}

.log-time {
  font-family: monospace;
  font-size: 0.82rem;
  color: #6c757d;
  white-space: nowrap;
}

/* ===== 工作台 ===== */
.workbench {
  width: 100%;
  max-width: 1400px;
}

.workbench-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.8rem 0 1rem;
  border-bottom: 2px solid #dee2e6;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.workbench-header h2 {
  flex: 1;
  font-size: 1.1rem;
  margin: 0;
}

.workbench-actions { display: flex; gap: 0.5rem; }

.back-btn {
  background: none;
  border: 1px solid #6c757d;
  color: #6c757d;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
}

.back-btn:hover { background: #f0f0f0; }

.workbench-body {
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
}

/* 左側影像 */
.invoice-image-panel {
  flex: 0 0 340px;
  position: sticky;
  top: 1rem;
}

.invoice-image-panel h3 {
  font-size: 0.95rem;
  margin-bottom: 0.6rem;
  color: #495057;
}

.image-wrapper {
  position: relative;
  display: inline-block;
  border: 2px solid #dee2e6;
  border-radius: 8px;
  overflow: hidden;
  width: 100%;
}

.invoice-img {
  display: block;
  width: 100%;
}



/* 右側 */
.right-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
}

.summary-section h3,
.edit-section .edit-label {
  font-size: 0.95rem;
  font-weight: 600;
  color: #495057;
  margin-bottom: 0.5rem;
  display: block;
}

.summary-table .cell-pair {
  display: flex;
  gap: 0.4rem;
  align-items: baseline;
  font-size: 0.85rem;
}

.cell-label {
  font-size: 0.72rem;
  color: #6c757d;
  min-width: 44px;
}

.edit-input {
  width: 90px;
  padding: 3px 6px;
  border: 1px solid #adb5bd;
  border-radius: 4px;
  font-size: 0.88rem;
}

.edit-input:focus {
  outline: 2px solid #007bff;
  border-color: transparent;
}

/* 稅額區 */
.totals-section {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 1rem 1.2rem;
}

.total-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 0.9rem;
  color: #495057;
}

.grand-total {
  border-top: 2px solid #dee2e6;
  margin-top: 6px;
  padding-top: 8px;
  font-size: 1rem;
  font-weight: 700;
  color: #1a1a2e;
}

.tolerance-hint {
  margin-top: 0.6rem;
  background: #fff3cd;
  border-left: 4px solid #ffc107;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 0.85rem;
  color: #856404;
}

/* 異常標註 */
.anomaly-textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #adb5bd;
  border-radius: 6px;
  font-size: 0.88rem;
  resize: vertical;
  box-sizing: border-box;
}

/* Audit Trail */
.audit-section {
  background: #fff8f0;
  border: 1px solid #ffe0b2;
  border-radius: 8px;
  padding: 0.8rem 1rem;
}

.audit-section h4 {
  margin: 0 0 0.5rem;
  font-size: 0.9rem;
  color: #e65100;
}

.audit-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.audit-entry {
  font-size: 0.82rem;
  color: #555;
  padding: 3px 0;
  border-bottom: 1px dashed #ffe0b2;
}

.audit-time {
  font-family: monospace;
  color: #e65100;
  margin-right: 6px;
}

/* ===== 退回原因 Modal ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal-box {
  background: #fff;
  border-radius: 12px;
  padding: 2rem;
  width: 480px;
  max-width: 94vw;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.modal-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: #dc3545;
  margin: 0;
}

.modal-sub {
  font-size: 0.85rem;
  color: #6c757d;
  margin: 0;
}

.required {
  color: #dc3545;
  margin-left: 3px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  margin-top: 0.4rem;
}

.back-modal-btn {
  background: #6c757d;
}

/* ===== Log 展開細項 ===== */
.log-detail-cell { text-align: center; }

.detail-toggle-btn {
  background: none;
  border: 1px solid #007bff;
  color: #007bff;
  padding: 2px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.78rem;
  transition: background 0.15s, color 0.15s;
}

.detail-toggle-btn:hover {
  background: #007bff;
  color: #fff;
}

.log-detail-row td {
  background: #f8f9fa;
  padding: 0.8rem 1rem !important;
  border-left: 4px solid #007bff !important;
}

.log-snapshot {
  max-width: 100%;
}

.snapshot-header {
  margin-bottom: 0.5rem;
  font-size: 0.88rem;
  color: #495057;
}

.snapshot-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}

.snapshot-table th,
.snapshot-table td {
  padding: 5px 10px;
  border: 1px solid #dee2e6;
  text-align: left;
}

.snapshot-table th {
  background: #e8eeff;
  font-weight: 600;
  font-size: 0.78rem;
}

.changed-val {
  color: #dc3545;
  font-weight: 600;
}

.orig-val {
  font-size: 0.75rem;
  color: #6c757d;
  font-weight: 400;
}

/* ===== Fade 動畫 ===== */
.fade-enter-active,
.fade-leave-active { transition: opacity 0.25s; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }
</style>
