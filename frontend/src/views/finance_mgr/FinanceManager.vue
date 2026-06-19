<template>
  <div class="fm-container">
    <div class="fm-header">
      <div>
        <h1 class="fm-title">{{ $t('finance_mgr.manager_group_dashboard') }}</h1>
      </div>
      <button @click="handleExportReport" class="btn-export">
        {{ $t('finance_mgr.export_report') }}
      </button>
    </div>

    <div class="stats-grid">
      <div class="stat-card total-count-card">
        <div class="stat-num">{{ allRecords.length }}</div>
        <div class="stat-label">{{ $t('finance_mgr.all_groups') }}</div>
      </div>
      <div class="stat-card approved-card">
        <div class="stat-num">{{ approvedCount }}</div>
        <div class="stat-label">{{ $t('finance_mgr.approved') }}</div>
      </div>
      <div class="stat-card pending-card">
        <div class="stat-num">{{ pendingCount }}</div>
        <div class="stat-label">{{ $t('finance_mgr.pending') }}</div>
      </div>
      <div class="stat-card rejected-card">
        <div class="stat-num">{{ onHoldCount }}</div>
        <div class="stat-label">{{ $t('finance_mgr.on_hold') }}</div>
      </div>
      <div class="stat-card total-card">
        <div class="stat-num amount-stat">{{ formatAmount(totalAmount) }}</div>
        <div class="stat-label">{{ $t('finance_mgr.application_amount') }}</div>
      </div>
    </div>

    <div class="fm-card">
      <div class="card-toolbar">
        <div>
          <h2 class="card-title">{{ $t('finance_mgr.group_list') }}</h2>
        </div>
        <span class="record-count">{{ exportRecords.length }} / {{ dateFilteredRecords.length }} {{ $t('finance_mgr.records') }}</span>
      </div>

      <div class="filter-panel">
        <label class="filter-field search-field">
          <span>{{ $t('finance_mgr.search') }}</span>
          <input v-model.trim="keywordFilter" type="search" :placeholder="$t('finance_mgr.group_search_placeholder')" />
        </label>
        <label class="filter-field">
          <span>{{ $t('finance_mgr.review_status') }}</span>
          <div class="segmented-control">
            <button type="button" :class="{ active: selectedStatusFilters.length === 0 }" @click="clearStatusFilters">{{ $t('finance_mgr.all') }}</button>
            <button type="button" :class="{ active: isStatusSelected('approved') }" @click="toggleStatusFilter('approved')">{{ $t('finance_mgr.approved') }}</button>
            <button type="button" :class="{ active: isStatusSelected('pending') }" @click="toggleStatusFilter('pending')">{{ $t('finance_mgr.pending') }}</button>
            <button type="button" :class="{ active: isStatusSelected('on_hold') }" @click="toggleStatusFilter('on_hold')">{{ $t('finance_mgr.on_hold') }}</button>
          </div>
        </label>
        <label class="filter-field">
          <span>{{ $t('finance_mgr.date_range') }}</span>
          <select v-model="datePreset">
            <option value="all">{{ $t('finance_mgr.all_dates') }}</option>
            <option value="7">{{ $t('finance_mgr.last_7_days') }}</option>
            <option value="30">{{ $t('finance_mgr.last_month') }}</option>
            <option value="90">{{ $t('finance_mgr.last_quarter') }}</option>
            <option value="180">{{ $t('finance_mgr.last_half_year') }}</option>
            <option value="custom">{{ $t('finance_mgr.custom_range') }}</option>
          </select>
        </label>
        <label class="filter-field date-field" :class="{ disabled: datePreset !== 'custom' }">
          <span>{{ $t('finance_mgr.start_date') }}</span>
          <input v-model="dateFrom" type="date" :disabled="datePreset !== 'custom'" />
        </label>
        <label class="filter-field date-field" :class="{ disabled: datePreset !== 'custom' }">
          <span>{{ $t('finance_mgr.end_date') }}</span>
          <input v-model="dateTo" type="date" :disabled="datePreset !== 'custom'" />
        </label>
        <button class="btn-reset" type="button" @click="resetFilters">{{ $t('finance_mgr.clear_filters') }}</button>
      </div>

      <div class="table-responsive">
        <table class="modern-table review-table">
          <colgroup>
            <col class="col-po" />
            <col class="col-vendor" />
            <col class="col-related" />
            <col class="col-date" />
            <col class="col-amount" />
            <col class="col-status" />
            <col class="col-action" />
          </colgroup>
          <thead>
            <tr>
              <th>{{ $t('finance_mgr.po_no') }}</th>
              <th>{{ $t('finance_mgr.vendor') }}</th>
              <th>{{ $t('finance_mgr.related_documents') }}</th>
              <th>{{ $t('finance_mgr.application_date') }}</th>
              <th>{{ $t('finance_mgr.application_amount') }}</th>
              <th>{{ $t('finance_mgr.status') }}</th>
              <th>{{ $t('finance_mgr.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loadError">
              <td colspan="7" class="empty-cell">{{ loadError }}</td>
            </tr>
            <tr v-else-if="isLoading">
              <td colspan="7" class="empty-cell">{{ $t('finance_mgr.loading_records') }}</td>
            </tr>
            <tr v-else-if="!isLoading && exportRecords.length === 0">
              <td colspan="7" class="empty-cell">{{ $t('finance_mgr.no_records') }}</td>
            </tr>
            <tr v-for="record in exportRecords" :key="record.rowKey">
              <td>
                <div class="document-cell">
                  <strong :title="record.poNo || $t('finance_mgr.not_provided')">{{ record.poNo || $t('finance_mgr.not_provided') }}</strong>
                  <span>{{ $t('finance_mgr.po_status') }}: {{ groupStatusText(record) }}</span>
                </div>
              </td>
              <td>
                <div class="person-cell">
                  <strong>{{ record.vendorName || '-' }}</strong>
                </div>
              </td>
              <td>
                <div class="related-cell">
                  <span :title="record.purchaseNo || '-'">
                    <b>PO</b>
                    <span class="related-value">{{ record.purchaseNo || '-' }}</span>
                  </span>
                  <span :title="record.grNo || '-'">
                    <b>GR</b>
                    <span class="related-value">{{ record.grNo || '-' }}</span>
                  </span>
                  <span :title="record.invoiceNo || '-'">
                    <b>INV</b>
                    <span class="related-value">{{ record.invoiceNo || '-' }}</span>
                  </span>
                </div>
              </td>
              <td class="text-muted">{{ formatDateTime(record.date) }}</td>
              <td class="text-amount">{{ formatAmount(record.amount) }}</td>
              <td>
                <span :class="['status-pill', record.statusClass]">
                  {{ groupStatusText(record) }}
                </span>
              </td>
              <td>
                <button class="btn-table-action" type="button" @click="openClaimDetail(record)">
                  {{ $t('finance_mgr.view') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <transition name="fade">
      <div v-if="showExportDialog" class="dialog-overlay" @click.self="closeExportDialog">
        <div class="dialog-box">
          <div class="dialog-header">
            <h2>{{ $t('finance_mgr.export_report') }}</h2>
            <button class="btn-close" @click="closeExportDialog">&#x2715;</button>
          </div>
          <div class="dialog-table">
            <table class="modern-table">
              <thead>
                <tr>
                  <th><input type="checkbox" @change="toggleSelectAll" /></th>
                  <th>{{ $t('finance_mgr.po_no') }}</th>
                  <th>{{ $t('finance_mgr.vendor') }}</th>
                  <th>{{ $t('finance_mgr.gr_no') }}</th>
                  <th>{{ $t('finance_mgr.invoice_no') }}</th>
                  <th>{{ $t('finance_mgr.application_date') }}</th>
                  <th>{{ $t('finance_mgr.application_amount') }}</th>
                  <th>{{ $t('finance_mgr.status') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="record in exportRecords" :key="record.rowKey">
                  <td><input type="checkbox" v-model="selectedRecords" :value="record" /></td>
                  <td class="text-bold">{{ record.poNo || $t('finance_mgr.not_provided') }}</td>
                  <td>{{ record.vendorName || '-' }}</td>
                  <td>{{ record.grNo || '-' }}</td>
                  <td>{{ record.invoiceNo || '-' }}</td>
                  <td class="text-muted">{{ formatDateTime(record.date) }}</td>
                  <td class="text-amount">{{ formatAmount(record.amount) }}</td>
                  <td>
                    <span :class="['status-pill', record.statusClass]">
                      {{ groupStatusText(record) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="dialog-footer">
            <span class="selected-count">{{ selectedRecords.length }} {{ $t('finance_mgr.selected') }}</span>
            <div class="dialog-actions">
              <button @click="closeExportDialog" class="btn-ghost">{{ $t('finance_mgr.cancel') }}</button>
              <button @click="exportToPDF" class="btn-primary" :disabled="selectedRecords.length === 0">
                {{ $t('finance_mgr.export') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div v-if="showDetailDialog" class="dialog-overlay" @click.self="closeDetailDialog">
        <div class="dialog-box detail-dialog">
          <div class="dialog-header">
            <div>
              <h2>{{ $t('finance_mgr.group_detail_title') }}</h2>
              <p class="dialog-subtitle">{{ detailGroup.poNo || activeRecord?.poNo || '-' }}</p>
            </div>
            <button class="btn-close" @click="closeDetailDialog">&#x2715;</button>
          </div>

          <div class="detail-body">
            <div v-if="detailError" class="detail-error">{{ detailError }}</div>
            <div v-else-if="isDetailLoading" class="empty-cell">{{ $t('finance_mgr.loading_detail') }}</div>
            <template v-else>
              <section class="detail-section">
                <h3>{{ $t('finance_mgr.match_group_info') }}</h3>
                <div class="detail-grid">
                  <div>
                    <span>{{ $t('finance_mgr.po_no') }}</span>
                    <strong>{{ detailGroup.poNo || activeRecord?.poNo || '-' }}</strong>
                  </div>
                  <div>
                    <span>{{ $t('finance_mgr.vendor') }}</span>
                    <strong>{{ detailVendorName || '-' }}</strong>
                  </div>
                  <div>
                    <span>{{ $t('finance_mgr.application_date') }}</span>
                    <strong>{{ formatDateTime(detailGroup.applyDate || activeRecord?.date) }}</strong>
                  </div>
                  <div>
                    <span>{{ $t('finance_mgr.status') }}</span>
                    <strong>{{ groupStatusText(detailGroup) || activeRecordStatusText || '-' }}</strong>
                  </div>
                </div>
              </section>

              <details class="detail-section expandable-section">
                <summary>
                  <span>{{ $t('finance_mgr.purchase_order') }}</span>
                  <strong>{{ detailPoNo }}</strong>
                </summary>
                <div class="detail-grid">
                  <div>
                    <span>{{ $t('finance_mgr.po_no') }}</span>
                    <strong>{{ detailPoNo }}</strong>
                  </div>
                  <div>
                    <span>{{ $t('finance_mgr.application_amount') }}</span>
                    <strong>{{ formatOptionalAmount(detailPurchaseAmount) }}</strong>
                  </div>
                  <div>
                    <span>{{ $t('finance_mgr.vendor') }}</span>
                    <strong>{{ detailVendorName || '-' }}</strong>
                  </div>
                </div>
                <div class="document-preview">
                  <h4>{{ $t('finance_mgr.purchase_order_attachment') }}</h4>
                  <div v-if="documentAttachmentErrors.purchaseOrder" :class="documentAttachmentClass('purchaseOrder')">{{ documentAttachmentErrors.purchaseOrder }}</div>
                  <div v-else-if="documentAttachmentUrls.purchaseOrder" class="attachment-preview compact-preview">
                    <img v-if="isPreviewImage(documentAttachmentUrls.purchaseOrder)" :src="documentAttachmentUrls.purchaseOrder" :alt="$t('finance_mgr.purchase_order_attachment')" />
                    <iframe v-else-if="isPreviewPdf(documentAttachmentUrls.purchaseOrder)" :src="documentAttachmentUrls.purchaseOrder" :title="$t('finance_mgr.purchase_order_attachment')"></iframe>
                    <a v-else :href="documentAttachmentUrls.purchaseOrder" target="_blank" rel="noopener noreferrer" class="attachment-link">{{ $t('finance_mgr.open_attachment') }}</a>
                  </div>
                  <div v-else class="nested-empty">{{ $t('finance_mgr.no_attachment') }}</div>
                </div>
              </details>

              <details class="detail-section expandable-section">
                <summary>
                  <span>{{ $t('finance_mgr.goods_receipt') }}</span>
                  <strong>{{ detailGrNo }}</strong>
                </summary>
                <div class="detail-grid">
                  <div>
                    <span>{{ $t('finance_mgr.gr_no') }}</span>
                    <strong>{{ detailGrNo }}</strong>
                  </div>
                </div>
                <div class="document-preview">
                  <h4>{{ $t('finance_mgr.goods_receipt_attachment') }}</h4>
                  <div v-if="documentAttachmentErrors.goodsReceipt" :class="documentAttachmentClass('goodsReceipt')">{{ documentAttachmentErrors.goodsReceipt }}</div>
                  <div v-else-if="documentAttachmentUrls.goodsReceipt" class="attachment-preview compact-preview">
                    <img v-if="isPreviewImage(documentAttachmentUrls.goodsReceipt)" :src="documentAttachmentUrls.goodsReceipt" :alt="$t('finance_mgr.goods_receipt_attachment')" />
                    <iframe v-else-if="isPreviewPdf(documentAttachmentUrls.goodsReceipt)" :src="documentAttachmentUrls.goodsReceipt" :title="$t('finance_mgr.goods_receipt_attachment')"></iframe>
                    <a v-else :href="documentAttachmentUrls.goodsReceipt" target="_blank" rel="noopener noreferrer" class="attachment-link">{{ $t('finance_mgr.open_attachment') }}</a>
                  </div>
                  <div v-else class="nested-empty">{{ $t('finance_mgr.no_attachment') }}</div>
                </div>
              </details>

              <details class="detail-section expandable-section">
                <summary>
                  <span>{{ $t('finance_mgr.invoice_info') }}</span>
                  <strong>{{ detailInvoiceNo }}</strong>
                </summary>
                <div class="detail-grid">
                  <div>
                    <span>{{ $t('finance_mgr.invoice_no') }}</span>
                    <strong>{{ detailInvoiceNo }}</strong>
                  </div>
                  <div>
                    <span>{{ $t('finance_mgr.invoice_date') }}</span>
                    <strong>{{ formatDateTime(detailInvoiceDate) }}</strong>
                  </div>
                  <div>
                    <span>{{ $t('finance_mgr.application_amount') }}</span>
                    <strong>{{ formatOptionalAmount(detailInvoiceAmount) }}</strong>
                  </div>
                </div>
                <div class="document-preview">
                  <h4>{{ $t('finance_mgr.invoice_attachment') }}</h4>
                  <div v-if="documentAttachmentErrors.invoice" :class="documentAttachmentClass('invoice')">{{ documentAttachmentErrors.invoice }}</div>
                  <div v-else-if="documentAttachmentUrls.invoice" class="attachment-preview compact-preview">
                    <img v-if="isPreviewImage(documentAttachmentUrls.invoice)" :src="documentAttachmentUrls.invoice" :alt="$t('finance_mgr.invoice_attachment')" />
                    <iframe v-else-if="isPreviewPdf(documentAttachmentUrls.invoice)" :src="documentAttachmentUrls.invoice" :title="$t('finance_mgr.invoice_attachment')"></iframe>
                    <a v-else :href="documentAttachmentUrls.invoice" target="_blank" rel="noopener noreferrer" class="attachment-link">{{ $t('finance_mgr.open_attachment') }}</a>
                  </div>
                  <div v-else class="nested-empty">{{ $t('finance_mgr.no_attachment') }}</div>
                </div>
              </details>

              <section v-if="detailAttachmentSource" class="detail-section">
                <h3>{{ $t('finance_mgr.attachment_preview') }}</h3>
                <div v-if="attachmentError" class="detail-error">{{ attachmentError }}</div>
                <div v-else-if="!detailAttachmentUrl" class="empty-cell">{{ $t('finance_mgr.loading_attachment') }}</div>
                <div v-else class="attachment-preview">
                  <img v-if="isImageAttachment" :src="detailAttachmentUrl" :alt="$t('finance_mgr.attachment')" />
                  <iframe v-else-if="isPdfAttachment" :src="detailAttachmentUrl" :title="$t('finance_mgr.attachment')"></iframe>
                  <div v-else class="preview-fallback">
                    <a :href="detailAttachmentUrl" target="_blank" rel="noopener noreferrer" class="attachment-link">
                      {{ $t('finance_mgr.open_attachment') }}
                    </a>
                  </div>
                </div>
              </section>

              <section v-if="detailPurchaseItems.length" class="detail-section">
                <h3>{{ $t('finance_mgr.item_detail') }}</h3>
                <div class="table-responsive">
                  <table class="modern-table compact-table">
                    <thead>
                      <tr>
                        <th>{{ $t('finance_mgr.item_name') }}</th>
                        <th>{{ $t('finance_mgr.quantity') }}</th>
                        <th>{{ $t('finance_mgr.unit_price') }}</th>
                        <th>{{ $t('finance_mgr.amount') }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(item, index) in detailPurchaseItems" :key="index">
                        <td>{{ item.itemName || '-' }}</td>
                        <td>{{ item.quantity ?? '-' }}</td>
                        <td>{{ item.unitPrice !== '' && item.unitPrice !== null && item.unitPrice !== undefined ? formatAmount(item.unitPrice) : '-' }}</td>
                        <td>{{ item.amount !== '' && item.amount !== null && item.amount !== undefined ? formatAmount(item.amount) : '-' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>
            </template>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue';
import { useI18n } from 'vue-i18n';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import { supabase } from '@/supabase.js';

const { t } = useI18n();
const showExportDialog = ref(false);
const allRecords = ref([]);
const selectedRecords = ref([]);
const isLoading = ref(false);
const loadError = ref('');
const showDetailDialog = ref(false);
const isDetailLoading = ref(false);
const detailError = ref('');
const activeRecord = ref(null);
const activeDetail = ref({ claim: {}, invoice: {} });
const attachmentObjectUrl = ref('');
const attachmentError = ref('');
const documentAttachmentUrls = ref({ purchaseOrder: '', goodsReceipt: '', invoice: '' });
const documentAttachmentTypes = ref({ purchaseOrder: '', goodsReceipt: '', invoice: '' });
const documentAttachmentErrors = ref({ purchaseOrder: '', goodsReceipt: '', invoice: '' });
const keywordFilter = ref('');
const selectedStatusFilters = ref([]);
const datePreset = ref('all');
const dateFrom = ref('');
const dateTo = ref('');

const MANAGER_API_BASE = '/api/manager';
const itemTableLabels = computed(() => ({
  itemName: t('finance_mgr.item_name'),
  quantity: t('finance_mgr.quantity'),
  unitPrice: t('finance_mgr.unit_price'),
  amount: t('finance_mgr.amount'),
  noItems: t('finance_mgr.no_items'),
}));
const DocumentItemsTable = {
  props: {
    items: { type: Array, default: () => [] },
    labels: { type: Object, required: true },
    formatAmount: { type: Function, required: true },
  },
  setup(props) {
    return () => {
      if (!props.items.length) {
        return null;
      }
      return h('div', { class: 'table-responsive nested-items' }, [
        h('table', { class: 'modern-table compact-table' }, [
          h('thead', [
            h('tr', [
              h('th', props.labels.itemName),
              h('th', props.labels.quantity),
              h('th', props.labels.unitPrice),
              h('th', props.labels.amount),
            ]),
          ]),
          h('tbody', props.items.map((item, index) => h('tr', { key: index }, [
            h('td', item.itemName || '-'),
            h('td', item.quantity ?? '-'),
            h('td', item.unitPrice !== '' && item.unitPrice !== null && item.unitPrice !== undefined ? props.formatAmount(item.unitPrice) : '-'),
            h('td', item.amount !== '' && item.amount !== null && item.amount !== undefined ? props.formatAmount(item.amount) : '-'),
          ]))),
        ]),
      ]);
    };
  },
};

const dateFilteredRecords = computed(() => allRecords.value.filter(record => isInSelectedDateRange(record.date)));
const exportRecords = computed(() => {
  const filtered = dateFilteredRecords.value.filter(record => {
    if (selectedStatusFilters.value.length && !selectedStatusFilters.value.includes(record.statusClass)) return false;
    if (!matchesKeyword(record)) return false;
    return true;
  });

  return [...filtered].sort((a, b) => {
    const statusDiff = statusRank(a.statusClass) - statusRank(b.statusClass);
    if (statusDiff !== 0) return statusDiff;
    return dateValue(b.date) - dateValue(a.date);
  });
});
const statRecords = computed(() => exportRecords.value);
const approvedCount = computed(() => statRecords.value.filter(r => r.status && r.status.includes('approved')).length);
const pendingCount = computed(() => statRecords.value.filter(r => r.status && r.status.includes('pending')).length);
const onHoldCount = computed(() => statRecords.value.filter(r => r.status && r.status.includes('on_hold')).length);
const totalAmount = computed(() => statRecords.value.reduce((sum, r) => sum + (Number(r.amount) || 0), 0));
const detailClaim = computed(() => activeDetail.value?.claim || {});
const detailGroup = computed(() => activeDetail.value?.group || activeDetail.value?.claim || {});
const detailInvoice = computed(() => activeDetail.value?.invoice || detailGroup.value?.invoice || activeDetail.value?.detail?.invoice || {});
const detailPurchaseOrder = computed(() => firstDocument(detailGroup.value?.purchaseOrder, detailGroup.value?.purchase_order, detailGroup.value?.po, activeDetail.value?.detail?.purchaseOrder, activeDetail.value?.detail?.purchase_order, activeDetail.value?.detail?.po));
const detailGoodsReceipt = computed(() => firstDocument(detailGroup.value?.goodsReceipt, detailGroup.value?.goods_receipt, detailGroup.value?.gr, activeDetail.value?.detail?.goodsReceipt, activeDetail.value?.detail?.goods_receipt, activeDetail.value?.detail?.gr));
const activeRecordStatusText = computed(() => activeRecord.value?.status ? t(activeRecord.value.status) : '');
const detailApplicationNo = computed(() => detailClaim.value.applicationNo || detailClaim.value.application_no || activeRecord.value?.applicationNo || '');
const detailPurchaseNo = computed(() => invoiceValue('purchaseNo', 'purchase_no', 'purchaseOrderNo', 'purchase_order_no', 'poNo', 'po_no') || detailClaim.value.purchaseNo || detailClaim.value.poNo || '');
const detailPoNo = computed(() => documentValue(detailPurchaseOrder.value, 'poNo', 'po_no', 'docNo', 'doc_no') || detailGroup.value.poNo || activeRecord.value?.poNo || '-');
const detailGrNo = computed(() => documentValue(detailGoodsReceipt.value, 'grNo', 'gr_no', 'docNo', 'doc_no') || detailGroup.value.grNo || '-');
const detailInvoiceNo = computed(() => documentValue(detailInvoice.value, 'invoiceNo', 'invoice_no', 'docNo', 'doc_no') || detailGroup.value.invoiceNo || '-');
const detailApplicantName = computed(() => purchaseOrderApplicantName(detailPurchaseOrder.value) || detailGroup.value.applicantName || activeRecord.value?.applicantName || '-');
const detailVendorName = computed(() => detailGroup.value.vendorName || documentValue(detailPurchaseOrder.value, 'vendorName', 'vendor_name') || nestedValueFrom(detailPurchaseOrder.value, 'vendor', 'name') || documentValue(detailInvoice.value, 'vendorName', 'vendor_name') || nestedValueFrom(detailInvoice.value, 'vendor', 'name') || '-');
const detailGrDate = computed(() => documentValue(detailGoodsReceipt.value, 'receivedDate', 'received_date', 'receiptDate', 'receipt_date', 'grDate', 'gr_date', 'createdAt', 'created_at'));
const detailInvoiceDate = computed(() => documentValue(detailInvoice.value, 'invoiceDate', 'invoice_date', 'date'));
const detailPurchaseAmount = computed(() => purchaseAmount(activeDetail.value?.detail || detailGroup.value || activeRecord.value || {}) || detailGroup.value.amount || activeRecord.value?.amount || '');
const detailInvoiceAmount = computed(() => {
  return hasDocumentData(detailInvoice.value) ? detailPurchaseAmount.value : '';
});
const detailPurchaseItems = computed(() => normalizeItems(documentValue(detailPurchaseOrder.value, 'items') || detailPurchaseOrder.value.items || []));
const detailGoodsReceiptItems = computed(() => normalizeItems(documentValue(detailGoodsReceipt.value, 'items') || detailGoodsReceipt.value.items || []));
const detailInvoiceItems = computed(() => normalizeItems(detailInvoice.value.items || detailInvoice.value.invoiceItems || detailInvoice.value.invoice_items || detailInvoice.value.formData?.items || []));
const detailAttachmentSource = computed(() => {
  const claim = detailClaim.value || {};
  const invoice = detailInvoice.value || {};
  const latestFile = invoice.latestFile || invoice.file || {};
  const files = Array.isArray(invoice.files) ? invoice.files : [];
  const firstFile = files[0] || {};
  return claim.attachmentUrl
    || invoice.attachmentUrl
    || invoice.invoiceImageUrl
    || latestFile.url
    || latestFile.publicUrl
    || firstFile.url
    || firstFile.publicUrl
    || '';
});
const detailAttachmentUrl = computed(() => attachmentObjectUrl.value || normalizeAttachmentUrl(detailAttachmentSource.value));
const isImageAttachment = computed(() => /\.(png|jpe?g|gif|webp|svg)(\?.*)?$/i.test(detailAttachmentSource.value || detailAttachmentUrl.value));
const isPdfAttachment = computed(() => /\.pdf(\?.*)?$/i.test(detailAttachmentSource.value || detailAttachmentUrl.value));

function isPreviewImage(url) {
  const contentType = contentTypeForPreviewUrl(url);
  if (contentType) return contentType.startsWith('image/');
  return /\.(png|jpe?g|gif|webp|svg)(\?.*)?$/i.test(url || '');
}

function isPreviewPdf(url) {
  const contentType = contentTypeForPreviewUrl(url);
  if (contentType) return contentType === 'application/pdf';
  return /\.pdf(\?.*)?$/i.test(url || '');
}

function contentTypeForPreviewUrl(url) {
  const match = Object.entries(documentAttachmentUrls.value).find(([, objectUrl]) => objectUrl === url);
  return match ? documentAttachmentTypes.value[match[0]] : '';
}

function handleExportReport() {
  showExportDialog.value = true;
}

function closeExportDialog() {
  showExportDialog.value = false;
  selectedRecords.value = [];
}

function closeDetailDialog() {
  showDetailDialog.value = false;
  activeRecord.value = null;
  activeDetail.value = { claim: {}, invoice: {} };
  detailError.value = '';
  clearAttachmentObjectUrl();
  clearDocumentAttachmentUrls();
}

function toggleSelectAll(event) {
  if (event.target.checked) {
    selectedRecords.value = [...exportRecords.value];
  } else {
    selectedRecords.value = [];
  }
}

async function exportToPDF() {
  const rows = selectedRecords.value;
  const report = document.createElement('div');
  report.className = 'pdf-report';
  report.innerHTML = buildReportHtml(rows);
  document.body.appendChild(report);

  try {
    const canvas = await html2canvas(report, {
      backgroundColor: '#ffffff',
      scale: 2,
      useCORS: true,
    });
    const pdf = new jsPDF('p', 'mm', 'a4');
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const margin = 10;
    const imgWidth = pageWidth - margin * 2;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    const pageCanvasHeight = Math.floor((canvas.width * (pageHeight - margin * 2)) / imgWidth);
    let renderedHeight = 0;

    while (renderedHeight < canvas.height) {
      const sliceHeight = Math.min(pageCanvasHeight, canvas.height - renderedHeight);
      const pageCanvas = document.createElement('canvas');
      pageCanvas.width = canvas.width;
      pageCanvas.height = sliceHeight;
      const context = pageCanvas.getContext('2d');
      context.drawImage(canvas, 0, renderedHeight, canvas.width, sliceHeight, 0, 0, canvas.width, sliceHeight);
      const pageImgHeight = (sliceHeight * imgWidth) / canvas.width;
      if (renderedHeight > 0) pdf.addPage();
      pdf.addImage(pageCanvas.toDataURL('image/png'), 'PNG', margin, margin, imgWidth, pageImgHeight);
      renderedHeight += sliceHeight;
    }

    pdf.save(`review-records-${new Date().toISOString().slice(0, 10)}.pdf`);
    closeExportDialog();
  } finally {
    report.remove();
  }
}

// 轉換 API 回傳資料為前端顯示格式
function mapApiDataToRecords(apiData) {
  return apiData.map((row, idx) => {
    const status = statusKey(row);
    const poNo = purchaseNo(row);
    const grNo = goodsReceiptNo(row);
    const invNo = invoiceNo(row);
    const id = poNo || row.groupId || row.group_id || row.id || `PO-GROUP-${idx+1}`;
    const appNo = applicationNo(row);
    return {
      rowKey: `${id}|${poNo}|${invNo}|${idx}`,
      id,
      displayId: row.groupId || row.group_id || row.matchGroupId || row.match_group_id || row.id || id,
      applicationNo: appNo,
      purchaseNo: poNo,
      poNo,
      grNo,
      groupId: row.groupId || row.group_id || row.matchGroupId || row.match_group_id || id,
      invoiceNo: invNo,
      applicantName: applicantName(row) || '-',
      applicantEmail: row.applicantEmail || row.applicant_email || '',
      vendorName: vendorName(row) || '-',
      date: row.applyDate || row.date || row.application_date || row.created_at || row.createdAt || '-',
      amount: purchaseAmount(row) || row.amount || row.totalAmount || row.total_amount || 0,
      status,
      statusClass: status.split('.')[1],
      groupStatus: row.groupStatus || row.group_status || row.status || '',
      statusDescription: row.statusDescription || row.status_description || '',
      attachmentUrl: row.attachmentUrl || row.attachment_url || '',
    };
  });
}

function normalizeAttachmentUrl(url) {
  if (!url) return '';
  if (/^(https?:|blob:|data:|\/)/i.test(url)) return url;
  return '';
}

function attachmentApiPath(url) {
  return `/attachments/${url.replace(/^\/+/, '').split('/').map(encodeURIComponent).join('/')}`;
}

async function managerFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const { data } = await supabase.auth.getSession();
  const token = data?.session?.access_token;
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return fetch(`${MANAGER_API_BASE}${path}`, { ...options, headers });
}

function clearAttachmentObjectUrl() {
  if (attachmentObjectUrl.value) {
    URL.revokeObjectURL(attachmentObjectUrl.value);
  }
  attachmentObjectUrl.value = '';
  attachmentError.value = '';
}

function clearDocumentAttachmentUrls() {
  Object.values(documentAttachmentUrls.value).forEach(url => {
    if (url) URL.revokeObjectURL(url);
  });
  documentAttachmentUrls.value = { purchaseOrder: '', goodsReceipt: '', invoice: '' };
  documentAttachmentTypes.value = { purchaseOrder: '', goodsReceipt: '', invoice: '' };
  documentAttachmentErrors.value = { purchaseOrder: '', goodsReceipt: '', invoice: '' };
}

async function loadDocumentAttachment(poNo, docType) {
  documentAttachmentErrors.value = { ...documentAttachmentErrors.value, [docType]: '' };
  try {
    const res = await managerFetch(`/match-groups/${encodeURIComponent(poNo)}/files/${docType}`);
    if (res.status === 404) {
      documentAttachmentErrors.value = { ...documentAttachmentErrors.value, [docType]: missingDocumentText(docType) };
      return;
    }
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const errorBody = await res.json();
        detail = errorBody.detail || detail;
      } catch (_) {
        detail = res.statusText || detail;
      }
      if (isMissingFileError(detail)) {
        documentAttachmentErrors.value = { ...documentAttachmentErrors.value, [docType]: missingDocumentText(docType) };
        return;
      }
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
    const objectUrl = URL.createObjectURL(await res.blob());
    documentAttachmentUrls.value = { ...documentAttachmentUrls.value, [docType]: objectUrl };
    documentAttachmentTypes.value = { ...documentAttachmentTypes.value, [docType]: res.headers.get('Content-Type') || '' };
  } catch (e) {
    documentAttachmentErrors.value = {
      ...documentAttachmentErrors.value,
      [docType]: `${t('finance_mgr.attachment_load_failed')} (${e.message || e})`,
    };
  }
}

function isMissingFileError(detail) {
  const text = typeof detail === 'string' ? detail : JSON.stringify(detail || {});
  return /file not found|找不到附件|找不到附件 metadata|找不到附件路徑/i.test(text);
}

function missingDocumentText(docType) {
  const keyMap = {
    purchaseOrder: 'finance_mgr.purchase_order_not_uploaded',
    goodsReceipt: 'finance_mgr.goods_receipt_not_uploaded',
    invoice: 'finance_mgr.invoice_not_uploaded',
  };
  return t(keyMap[docType] || 'finance_mgr.no_attachment');
}

function documentAttachmentClass(docType) {
  return documentAttachmentErrors.value[docType] === missingDocumentText(docType) ? 'nested-empty' : 'detail-error';
}

async function loadDocumentAttachments(poNo) {
  clearDocumentAttachmentUrls();
  await Promise.all([
    loadDocumentAttachment(poNo, 'purchaseOrder'),
    loadDocumentAttachment(poNo, 'goodsReceipt'),
    loadDocumentAttachment(poNo, 'invoice'),
  ]);
}

async function loadAttachmentObjectUrl(source) {
  clearAttachmentObjectUrl();
  if (!source || /^(https?:|blob:|data:|\/)/i.test(source)) return;
  try {
    const res = await managerFetch(attachmentApiPath(source));
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const errorBody = await res.json();
        detail = errorBody.detail || detail;
      } catch (_) {
        detail = res.statusText || detail;
      }
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
    attachmentObjectUrl.value = URL.createObjectURL(await res.blob());
  } catch (e) {
    attachmentError.value = `${t('finance_mgr.attachment_load_failed')} (${e.message || e})`;
  }
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function buildReportHtml(rows) {
  const headers = [
    t('finance_mgr.po_no'),
    t('finance_mgr.vendor'),
    t('finance_mgr.gr_no'),
    t('finance_mgr.invoice_no'),
    t('finance_mgr.application_date'),
    t('finance_mgr.application_amount'),
    t('finance_mgr.status'),
  ];
  const bodyRows = rows.map(record => `
    <tr>
      <td>${escapeHtml(record.poNo || t('finance_mgr.not_provided'))}</td>
      <td>${escapeHtml(record.vendorName || '-')}</td>
      <td>${escapeHtml(record.grNo || '-')}</td>
      <td>${escapeHtml(record.invoiceNo || '-')}</td>
      <td>${escapeHtml(formatDateTime(record.date))}</td>
      <td>${escapeHtml(formatAmount(record.amount))}</td>
      <td>${escapeHtml(groupStatusText(record))}</td>
    </tr>
  `).join('');

  return `
  <h1>${escapeHtml(t('finance_mgr.review_records'))}</h1>
  <div class="meta">${escapeHtml(new Date().toLocaleString('zh-TW'))} · ${rows.length} ${escapeHtml(t('finance_mgr.records'))}</div>
  <table>
    <thead><tr>${headers.map(header => `<th>${escapeHtml(header)}</th>`).join('')}</tr></thead>
    <tbody>${bodyRows}</tbody>
  </table>`;
}

function statusKey(row) {
  const statusCode = Number(row.statusCode ?? row.status_code);
  const statusText = row.groupStatus || row.group_status || row.status || row.statusDescription || row.status_description || '';
  if (['onHold', 'on_hold', 'hold', '暫緩'].includes(statusText)) return 'finance_mgr.on_hold';
  if (statusText === 'void' || statusText === '作廢') return 'finance_mgr.void';
  if (['approved', '已同意'].includes(statusText)) return 'finance_mgr.approved';
  if (['po_pending', 'missing_gr_invoice', 'missing_gr', 'missing_invoice', 'complete', 'pendingMatch', 'pending_match'].includes(statusText)) return 'finance_mgr.pending';
  if (statusCode === 2 || ['approved', '已同意'].includes(statusText)) return 'finance_mgr.approved';
  if (statusCode === 3 || ['rejected', '已拒絕'].includes(statusText)) return 'finance_mgr.rejected';
  return 'finance_mgr.pending';
}

function groupStatusText(record) {
  const raw = record?.groupStatus || record?.group_status || record?.statusDescription || record?.status_description || record?.status || '';
  const keyMap = {
    approved: 'finance_mgr.approved',
    '已同意': 'finance_mgr.approved',
    pending: 'finance_mgr.pending',
    '待核准': 'finance_mgr.pending',
    pendingMatch: 'finance_mgr.pending_match',
    pending_match: 'finance_mgr.pending_match',
    '待媒合': 'finance_mgr.pending_match',
    po_pending: 'finance_mgr.status_po_pending',
    '採購單待審': 'finance_mgr.status_po_pending',
    missing_gr_invoice: 'finance_mgr.status_missing_gr_invoice',
    '缺驗收單與發票': 'finance_mgr.status_missing_gr_invoice',
    missing_gr: 'finance_mgr.status_missing_gr',
    '缺驗收單': 'finance_mgr.status_missing_gr',
    missing_invoice: 'finance_mgr.status_missing_invoice',
    '缺發票': 'finance_mgr.status_missing_invoice',
    complete: 'finance_mgr.status_complete',
    onHold: 'finance_mgr.on_hold',
    on_hold: 'finance_mgr.on_hold',
    hold: 'finance_mgr.on_hold',
    '暫緩': 'finance_mgr.on_hold',
    rejected: 'finance_mgr.rejected',
    '已拒絕': 'finance_mgr.rejected',
    void: 'finance_mgr.void',
    '作廢': 'finance_mgr.void',
  };
  const key = keyMap[raw] || record?.status;
  return key ? t(key) : '-';
}

function purchaseNo(row) {
  return row.purchaseNo
    || row.purchase_no
    || row.purchaseOrderNo
    || row.purchase_order_no
    || row.poNo
    || row.po_no
    || row.formData?.purchaseNo
    || row.formData?.purchase_order_no
    || row.formData?.poNo
    || row.form_data?.purchaseNo
    || row.form_data?.purchase_order_no
    || row.form_data?.poNo
    || '';
}

function goodsReceiptNo(row) {
  const goodsReceipt = row.goodsReceipt || row.goods_receipt || row.gr;
  return row.grNo
    || row.gr_no
    || row.goodsReceiptNo
    || row.goods_receipt_no
    || documentValue(goodsReceipt, 'grNo', 'gr_no', 'docNo', 'doc_no', 'goodsReceiptNo', 'goods_receipt_no')
    || '';
}

function invoiceNo(row) {
  return row.invoiceNo
    || row.invoice_no
    || documentValue(row.invoice, 'invoiceNo', 'invoice_no', 'docNo', 'doc_no')
    || '';
}

function purchaseAmount(row) {
  return documentValue(row.purchaseOrder || row.purchase_order || row.po, 'totalAmount', 'total_amount')
    || documentValue(row.purchaseOrder || row.purchase_order || row.po, 'amount')
    || documentValue((row.purchaseOrder || row.purchase_order || row.po)?.formData || (row.purchaseOrder || row.purchase_order || row.po)?.form_data, 'totalAmount', 'total_amount', 'amount')
    || documentValue(row, 'purchaseTotalAmount', 'purchase_total_amount', 'poTotalAmount', 'po_total_amount')
    || '';
}

function vendorName(row) {
  const purchaseOrder = row.purchaseOrder || row.purchase_order || row.po;
  return row.vendorName
    || row.vendor_name
    || nestedValueFrom(row, 'vendor', 'name')
    || documentValue(purchaseOrder, 'vendorName', 'vendor_name')
    || nestedValueFrom(purchaseOrder, 'vendor', 'name')
    || documentValue(row.invoice, 'vendorName', 'vendor_name')
    || nestedValueFrom(row.invoice, 'vendor', 'name')
    || '';
}

function formatOptionalAmount(value) {
  if (value === undefined || value === null || value === '') return '-';
  return formatAmount(value);
}

function hasDocumentData(document) {
  return !!document && typeof document === 'object' && Object.keys(document).length > 0;
}

function firstDocument(...documents) {
  return documents.find(document => hasDocumentData(document)) || {};
}

function applicationNo(row, idx) {
  const claimId = row.claimId || row.claim_id || '';
  const displayClaimId = isUuidLike(claimId) ? '' : claimId;
  return row.applicationNo
    || row.application_no
    || row.claimNo
    || row.claim_no
    || row.requisitionNo
    || row.requisition_no
    || row.requestNo
    || row.request_no
    || row.formData?.applicationNo
    || row.formData?.application_no
    || row.formData?.claimNo
    || row.formData?.claim_no
    || row.formData?.requisitionNo
    || row.formData?.requisition_no
    || row.formData?.requestNo
    || row.formData?.request_no
    || displayClaimId
    || '';
}

function isUuidLike(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || ''));
}

function applicantName(row) {
  return purchaseOrderApplicantName(row.purchaseOrder || row.purchase_order || row.po)
    || row.purchaser
    || row.purchaser_name
    || row.applicantName
    || row.applicant_name
    || row.requesterName
    || row.requester_name
    || row.submitterName
    || row.submitter_name
    || row.createdByName
    || row.created_by_name
    || row.formData?.applicantName
    || row.formData?.applicant_name
    || row.formData?.applicant
    || row.formData?.requesterName
    || row.formData?.requester_name
    || row.formData?.submitterName
    || row.formData?.submitter_name
    || row.form_data?.applicantName
    || row.form_data?.applicant_name
    || row.form_data?.applicant
    || row.form_data?.requesterName
    || row.form_data?.requester_name
    || row.form_data?.submitterName
    || row.form_data?.submitter_name
    || '';
}

function purchaseOrderApplicantName(purchaseOrder) {
  return documentValue(
    purchaseOrder,
    'purchaser',
    'purchaserName',
    'purchaser_name',
    'requesterName',
    'requester_name',
    'applicantName',
    'applicant_name',
    'uploadedByName',
    'uploaded_by_name',
    'createdByName',
    'created_by_name',
    'employeeName',
    'employee_name'
  )
    || nestedValueFrom(purchaseOrder, 'requester', 'fullName')
    || nestedValueFrom(purchaseOrder, 'requester', 'full_name')
    || nestedValueFrom(purchaseOrder, 'requester', 'name')
    || nestedValueFrom(purchaseOrder, 'uploadedBy', 'fullName')
    || nestedValueFrom(purchaseOrder, 'uploadedBy', 'full_name')
    || nestedValueFrom(purchaseOrder, 'uploadedBy', 'name')
    || nestedValueFrom(purchaseOrder, 'uploaded_by', 'fullName')
    || nestedValueFrom(purchaseOrder, 'uploaded_by', 'full_name')
    || nestedValueFrom(purchaseOrder, 'uploaded_by', 'name')
    || nestedValueFrom(purchaseOrder, 'createdBy', 'fullName')
    || nestedValueFrom(purchaseOrder, 'createdBy', 'full_name')
    || nestedValueFrom(purchaseOrder, 'createdBy', 'name')
    || nestedValueFrom(purchaseOrder, 'created_by', 'fullName')
    || nestedValueFrom(purchaseOrder, 'created_by', 'full_name')
    || nestedValueFrom(purchaseOrder, 'created_by', 'name')
    || nestedValueFrom(purchaseOrder, 'employee', 'fullName')
    || nestedValueFrom(purchaseOrder, 'employee', 'full_name')
    || nestedValueFrom(purchaseOrder, 'employee', 'name')
    || '';
}

function matchesKeyword(record) {
  const keyword = keywordFilter.value.trim().toLowerCase();
  if (!keyword) return true;
  return [
    record.applicationNo,
    record.applicantName,
    record.applicantEmail,
    record.vendorName,
    record.poNo,
    record.purchaseNo,
    record.grNo,
    record.invoiceNo,
    record.groupId,
  ].some(value => String(value || '').toLowerCase().includes(keyword));
}

function formatAmount(value) {
  const amount = Number(value) || 0;
  return new Intl.NumberFormat('zh-TW', {
    style: 'currency',
    currency: 'TWD',
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDateTime(value) {
  if (!value) return '-';
  const text = String(value);
  const parsed = Date.parse(text);
  if (Number.isNaN(parsed)) return text || '-';
  const hasTime = /T|\d{1,2}:\d{2}/.test(text);
  return new Intl.DateTimeFormat('zh-TW', {
    timeZone: 'Asia/Taipei',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    ...(hasTime ? { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false } : {}),
  }).format(new Date(parsed));
}

function documentStatusText(document) {
  const status = documentValue(document, 'status', 'groupStatus', 'group_status');
  const labels = {
    approved: t('finance_mgr.approved'),
    pending: t('finance_mgr.pending'),
    pendingMatch: t('finance_mgr.pending_match'),
    pending_match: t('finance_mgr.pending_match'),
    rejected: t('finance_mgr.rejected'),
    onHold: t('finance_mgr.on_hold'),
    on_hold: t('finance_mgr.on_hold'),
    void: t('finance_mgr.void'),
  };
  return labels[status] || status || '-';
}

function normalizeItems(items) {
  if (!Array.isArray(items)) return [];
  return items.map(item => {
    const quantity = firstPresent(item.quantity, item.qty, item.poQty, item.po_qty, item.orderedQty, item.ordered_qty, item.invoiceQty, item.invoice_qty, item.receivedQty, item.received_qty, item.acceptedQty, item.accepted_qty);
    const unitPrice = firstPresent(item.unitPrice, item.unit_price, item.poUnitPrice, item.po_unit_price, item.invoiceUnitPrice, item.invoice_unit_price);
    const amount = firstPresent(item.lineAmount, item.line_amount, item.amount, item.poAmount, item.po_amount, computedLineAmount(quantity, unitPrice));
    return {
      itemName: item.itemName || item.item_name || item.description || item.name || '-',
      quantity,
      unitPrice,
      amount,
    };
  });
}

function firstPresent(...values) {
  return values.find(value => value !== undefined && value !== null && value !== '') ?? '';
}

function computedLineAmount(quantity, unitPrice) {
  if (quantity === '' || unitPrice === '') return '';
  const qty = Number(quantity);
  const price = Number(unitPrice);
  if (!Number.isFinite(qty) || !Number.isFinite(price)) return '';
  return qty * price;
}

function statusRank(statusClass) {
  return { approved: 1, pending: 2, on_hold: 3, void: 4, rejected: 5 }[statusClass] || 6;
}

function isStatusSelected(status) {
  return selectedStatusFilters.value.includes(status);
}

function toggleStatusFilter(status) {
  if (isStatusSelected(status)) {
    selectedStatusFilters.value = selectedStatusFilters.value.filter(item => item !== status);
    return;
  }
  selectedStatusFilters.value = [...selectedStatusFilters.value, status];
}

function clearStatusFilters() {
  selectedStatusFilters.value = [];
}

function dateValue(value) {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function startOfDay(date) {
  const nextDate = new Date(date);
  nextDate.setHours(0, 0, 0, 0);
  return nextDate;
}

function endOfDay(date) {
  const nextDate = new Date(date);
  nextDate.setHours(23, 59, 59, 999);
  return nextDate;
}

function isInSelectedDateRange(value) {
  const parsed = dateValue(value);
  if (!parsed) return datePreset.value === 'all';

  const recordDate = new Date(parsed);
  if (['7', '30', '90', '180'].includes(datePreset.value)) {
    const from = startOfDay(new Date());
    from.setDate(from.getDate() - Number(datePreset.value) + 1);
    return recordDate >= from && recordDate <= endOfDay(new Date());
  }

  if (datePreset.value === 'custom') {
    const from = dateFrom.value ? startOfDay(new Date(dateFrom.value)) : null;
    const to = dateTo.value ? endOfDay(new Date(dateTo.value)) : null;
    if (from && recordDate < from) return false;
    if (to && recordDate > to) return false;
  }

  return true;
}

function resetFilters() {
  keywordFilter.value = '';
  clearStatusFilters();
  datePreset.value = 'all';
  dateFrom.value = '';
  dateTo.value = '';
}

async function fetchManagerClaims() {
  return managerFetch('/match-groups');
}

async function openClaimDetail(record) {
  if (!record.poNo) {
    detailError.value = `${t('finance_mgr.detail_load_failed')} (${t('finance_mgr.missing_po_no')})`;
    return;
  }
  activeRecord.value = record;
  activeDetail.value = { group: { ...record }, invoice: {} };
  showDetailDialog.value = true;
  isDetailLoading.value = true;
  detailError.value = '';
  try {
    const res = await managerFetch(`/match-groups/${encodeURIComponent(record.poNo)}`);
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const errorBody = await res.json();
        detail = errorBody.detail || detail;
      } catch (_) {
        detail = res.statusText || detail;
      }
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
    activeDetail.value = await res.json();
    await loadAttachmentObjectUrl(detailAttachmentSource.value);
    await loadDocumentAttachments(record.poNo);
  } catch (e) {
    detailError.value = `${t('finance_mgr.detail_load_failed')} (${e.message || e})`;
  } finally {
    isDetailLoading.value = false;
  }
}

function invoiceValue(...keys) {
  const invoice = detailInvoice.value || {};
  const formData = invoice.formData || invoice.form_data || {};
  for (const key of keys) {
    if (invoice[key] !== undefined && invoice[key] !== null && invoice[key] !== '') return invoice[key];
    if (formData[key] !== undefined && formData[key] !== null && formData[key] !== '') return formData[key];
  }
  return '';
}

function documentValue(document, ...keys) {
  const source = document || {};
  const formData = source.formData || source.form_data || {};
  for (const key of keys) {
    if (source[key] !== undefined && source[key] !== null && source[key] !== '') return source[key];
    if (formData[key] !== undefined && formData[key] !== null && formData[key] !== '') return formData[key];
  }
  return '';
}

function nestedValueFrom(document, parentKey, childKey) {
  const parent = document?.[parentKey];
  if (!parent || typeof parent !== 'object') return '';
  return parent[childKey] || '';
}

onMounted(async () => {
  isLoading.value = true;
  loadError.value = '';
  try {
    const res = await fetchManagerClaims();
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const errorBody = await res.json();
        detail = errorBody.detail || detail;
      } catch (_) {
        detail = res.statusText || detail;
      }
      throw new Error(detail);
    }
    const data = await res.json();
    allRecords.value = Array.isArray(data) ? mapApiDataToRecords(data) : [];
  } catch (e) {
    allRecords.value = [];
    loadError.value = `${t('finance_mgr.load_failed')} (${e.message || e})`;
  } finally {
    isLoading.value = false;
  }
});
</script>

<style scoped>
.fm-container {
  background: #f5f7fb;
  min-height: 100vh;
  padding: 2rem 1.5rem 3rem;
  font-family: 'Inter', -apple-system, sans-serif;
  max-width: 1320px;
  margin: 0 auto;
}
.fm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}
.fm-title { font-size: 1.75rem; font-weight: 800; color: #111827; margin: 0 0 0.3rem 0; }
.fm-subtitle { color: #64748b; font-size: 0.95rem; margin: 0; }
.btn-export {
  background: #1d4ed8;
  color: #fff;
  border: none;
  padding: 0.75rem 1.35rem;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(29, 78, 216, 0.18);
  transition: background 0.2s, transform 0.15s;
}
.btn-export:hover { background: #1e40af; transform: translateY(-1px); }
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
  margin-bottom: 1.25rem;
}
.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 1rem 1.1rem;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
  border: 1px solid #e6edf5;
  border-top: 3px solid #e2e8f0;
}
.total-count-card { border-top-color: #475569; }
.approved-card { border-top-color: #16a34a; }
.pending-card  { border-top-color: #d97706; }
.rejected-card { border-top-color: #dc2626; }
.total-card    { border-top-color: #2563eb; }
.stat-num { font-size: 1.45rem; font-weight: 800; color: #1e293b; line-height: 1; }
.amount-stat { font-size: 1.2rem; }
.stat-label { font-size: 0.8rem; color: #64748b; margin-top: 0.45rem; }
.fm-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.06);
  padding: 1.4rem;
  border: 1px solid #e6edf5;
}
.card-toolbar {
  align-items: center;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
  margin-bottom: 1rem;
}
.card-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}
.card-caption {
  color: #64748b;
  font-size: 0.82rem;
  margin: 0.25rem 0 0;
}
.record-count {
  background: #eef2ff;
  border: 1px solid #dbe4ff;
  border-radius: 999px;
  color: #1d4ed8;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 0.35rem 0.7rem;
}
.filter-panel {
  align-items: end;
  background: #f8fafc;
  border: 1px solid #e6edf5;
  border-radius: 8px;
  display: grid;
  gap: 0.75rem;
  grid-template-columns: minmax(220px, 1.1fr) minmax(330px, 1.35fr) minmax(145px, 0.75fr) minmax(145px, 0.72fr) minmax(145px, 0.72fr) minmax(96px, auto);
  margin-bottom: 1rem;
  padding: 1rem;
}
.filter-field {
  display: grid;
  gap: 0.35rem;
  min-width: 0;
}
.filter-field span {
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 700;
}
.filter-field select,
.filter-field input {
  appearance: none;
  background: #fff;
  border: 1px solid #cfd9e6;
  border-radius: 8px;
  box-sizing: border-box;
  color: #1e293b;
  font: inherit;
  height: 42px;
  min-height: 42px;
  padding: 0.5rem 0.7rem;
  width: 100%;
}
.segmented-control {
  align-items: stretch;
  background: #eef2f7;
  border: 1px solid #d7e0ea;
  border-radius: 8px;
  box-sizing: border-box;
  display: grid;
  gap: 0.2rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  height: 42px;
  min-height: 42px;
  padding: 0.2rem;
}
.segmented-control button {
  background: transparent;
  border: 0;
  border-radius: 6px;
  color: #64748b;
  cursor: pointer;
  font: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  min-width: 0;
  padding: 0 0.45rem;
  white-space: nowrap;
}
.segmented-control button.active {
  background: #fff;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.1);
  color: #1d4ed8;
}
.filter-field select:focus,
.filter-field input:focus {
  border-color: #155bd5;
  box-shadow: 0 0 0 3px rgba(21, 91, 213, 0.12);
  outline: none;
}
.filter-field.disabled {
  opacity: 0.55;
}
.btn-reset {
  background: #fff;
  border: 1px solid #cfd9e6;
  border-radius: 8px;
  box-sizing: border-box;
  color: #475569;
  cursor: pointer;
  font-weight: 700;
  height: 42px;
  min-height: 42px;
  padding: 0 0.9rem;
  transition: background 0.2s, border-color 0.2s;
  white-space: nowrap;
}
.btn-reset:hover {
  background: #eef3f8;
  border-color: #b8c5d6;
}
.table-responsive { overflow-x: auto; }
.modern-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.9rem; }
.review-table {
  min-width: 980px;
  table-layout: fixed;
}
.review-table .col-po { width: 22%; }
.review-table .col-vendor { width: 15%; }
.review-table .col-related { width: 23%; }
.review-table .col-date { width: 12%; }
.review-table .col-amount { width: 12%; }
.review-table .col-status { width: 10%; }
.review-table .col-action { width: 6%; }
.modern-table th {
  background: #f4f7fb;
  padding: 0.75rem 0.9rem;
  color: #64748b;
  font-weight: 700;
  font-size: 0.75rem;
  letter-spacing: 0;
  border-bottom: 1px solid #e6edf5;
  white-space: nowrap;
  text-align: left;
}
.modern-table td {
  padding: 0.9rem;
  border-bottom: 1px solid #edf2f7;
  color: #475569;
  white-space: nowrap;
  vertical-align: middle;
}
.review-table th:nth-child(5),
.review-table td:nth-child(5) {
  text-align: right;
}
.review-table th:nth-child(6),
.review-table td:nth-child(6),
.review-table th:nth-child(7),
.review-table td:nth-child(7) {
  text-align: center;
}
.modern-table tbody tr:hover td { background: #f7fbff; }
.text-bold { font-weight: 700; color: #1e293b !important; }
.text-muted { color: #94a3b8 !important; }
.text-amount { font-weight: 600; color: #1e293b !important; }
.document-cell,
.person-cell,
.related-cell {
  display: grid;
  gap: 0.18rem;
}
.document-cell strong,
.person-cell strong {
  color: #1e293b;
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.document-cell span,
.person-cell span {
  color: #94a3b8;
  font-size: 0.78rem;
}
.related-cell span {
  align-items: center;
  color: #475569;
  display: inline-flex;
  gap: 0.8rem;
  min-width: max-content;
}
.related-cell b {
  background: #eef2f7;
  border-radius: 5px;
  color: #64748b;
  font-size: 0.68rem;
  min-width: 2rem;
  padding: 0.12rem 0.35rem;
  text-align: center;
}
.related-value {
  color: #1e293b;
  display: inline;
  font-weight: 500;
  min-width: max-content;
  overflow: visible;
  white-space: nowrap;
}
.empty-cell {
  text-align: center;
  color: #94a3b8 !important;
  padding: 2rem 1rem !important;
}
.attachment-link {
  color: #2563eb;
  font-weight: 600;
  text-decoration: none;
}
.attachment-link:hover { text-decoration: underline; }
.detail-link {
  background: transparent;
  border: 0;
  cursor: pointer;
  font: inherit;
  padding: 0;
}
.btn-table-action {
  background: #fff;
  border: 1px solid #cfd9e6;
  border-radius: 8px;
  color: #1d4ed8;
  cursor: pointer;
  font-weight: 700;
  padding: 0.42rem 0.75rem;
}
.btn-table-action:hover {
  background: #eef4ff;
  border-color: #b9c9e2;
}
.status-pill {
  padding: 0.28rem 0.65rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  display: inline-block;
}
.approved { background: #dcfce7; color: #15803d; }
.pending  { background: #fff7d6; color: #a16207; }
.rejected { background: #fee2e2; color: #dc2626; }
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15,23,42,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}
.dialog-box {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
  width: 100%;
  max-width: 680px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.3rem 1.5rem;
  border-bottom: 1px solid #f1f5f9;
}
.dialog-header h2 { margin: 0; font-size: 1.1rem; font-weight: 700; color: #1e293b; }
.dialog-subtitle {
  color: #64748b;
  font-size: 0.85rem;
  margin: 0.3rem 0 0;
}
.btn-close {
  background: none;
  border: none;
  font-size: 1rem;
  color: #94a3b8;
  cursor: pointer;
  padding: 0.3rem 0.5rem;
  border-radius: 6px;
  transition: background 0.2s;
}
.btn-close:hover { background: #f1f5f9; color: #475569; }
.dialog-table { padding: 1rem 1.5rem; overflow-y: auto; flex: 1; }
.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-top: 1px solid #f1f5f9;
  gap: 1rem;
}
.selected-count { font-size: 0.85rem; color: #64748b; }
.dialog-actions { display: flex; gap: 0.75rem; }
.btn-primary {
  background: #155bd5;
  color: #fff;
  border: none;
  padding: 0.6rem 1.4rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-primary:hover:not(:disabled) { background: #1049ad; }
.btn-primary:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-ghost {
  background: transparent;
  color: #64748b;
  border: 1.5px solid #e2e8f0;
  padding: 0.6rem 1.4rem;
  border-radius: 8px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-ghost:hover { background: #f8fafc; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.detail-dialog {
  max-width: 860px;
}
.detail-body {
  padding: 1.2rem 1.5rem 1.5rem;
  overflow-y: auto;
}
.detail-section {
  border-bottom: 1px solid #f1f5f9;
  padding: 0 0 1.2rem;
  margin-bottom: 1.2rem;
}
.detail-section:last-child {
  border-bottom: 0;
  margin-bottom: 0;
  padding-bottom: 0;
}
.detail-section h3 {
  color: #1e293b;
  font-size: 0.95rem;
  margin: 0 0 0.9rem;
}
.expandable-section {
  background: #fff;
}
.expandable-section summary {
  align-items: center;
  color: #1e293b;
  cursor: pointer;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
  list-style: none;
  margin-bottom: 0;
  min-height: 38px;
}
.expandable-section summary::-webkit-details-marker {
  display: none;
}
.expandable-section summary::before {
  color: #64748b;
  content: "▸";
  font-size: 0.85rem;
  margin-right: 0.35rem;
}
.expandable-section[open] summary {
  margin-bottom: 0.9rem;
}
.expandable-section[open] summary::before {
  content: "▾";
}
.expandable-section summary span {
  color: #1e293b;
  flex: 1;
  font-size: 0.95rem;
  font-weight: 700;
}
.expandable-section summary strong {
  color: #64748b;
  font-size: 0.84rem;
  font-weight: 700;
  overflow-wrap: anywhere;
  text-align: right;
}
.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.9rem 1rem;
}
.detail-grid div {
  min-width: 0;
}
.detail-grid span {
  color: #94a3b8;
  display: block;
  font-size: 0.75rem;
  margin-bottom: 0.25rem;
}
.detail-grid strong {
  color: #1e293b;
  display: block;
  font-size: 0.9rem;
  overflow-wrap: anywhere;
}
.detail-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #b91c1c;
  padding: 0.85rem 1rem;
}
.attachment-preview {
  background: #f8fafc;
  border: 1px solid #e6edf5;
  border-radius: 8px;
  min-height: 260px;
  overflow: hidden;
}
.attachment-preview img {
  display: block;
  max-height: 520px;
  max-width: 100%;
  object-fit: contain;
  width: 100%;
}
.attachment-preview iframe {
  border: 0;
  display: block;
  height: 520px;
  width: 100%;
}
.document-preview {
  margin-top: 1rem;
}
.document-preview h4 {
  color: #475569;
  font-size: 0.85rem;
  margin: 0 0 0.55rem;
}
.compact-preview {
  min-height: 180px;
}
.compact-preview img {
  max-height: 360px;
}
.compact-preview iframe {
  height: 360px;
}
.preview-fallback {
  align-items: center;
  display: flex;
  justify-content: center;
  min-height: 260px;
}
.compact-table th,
.compact-table td {
  white-space: normal;
}
.nested-items {
  margin-top: 1rem;
}
.nested-empty {
  background: #f8fafc;
  border: 1px dashed #d7e0ea;
  border-radius: 8px;
  color: #94a3b8;
  font-size: 0.85rem;
  margin-top: 1rem;
  padding: 0.8rem;
  text-align: center;
}
:global(.pdf-report) {
  background: #fff;
  color: #172033;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans TC", "Microsoft JhengHei", sans-serif;
  left: -10000px;
  padding: 32px;
  position: fixed;
  top: 0;
  width: 920px;
  z-index: -1;
}
:global(.pdf-report h1) {
  font-size: 24px;
  margin: 0 0 6px;
}
:global(.pdf-report .meta) {
  color: #667085;
  font-size: 13px;
  margin-bottom: 20px;
}
:global(.pdf-report table) {
  border-collapse: collapse;
  font-size: 13px;
  width: 100%;
}
:global(.pdf-report th) {
  background: #f1f5f9;
  color: #334155;
  text-align: left;
}
:global(.pdf-report th),
:global(.pdf-report td) {
  border: 1px solid #dbe3ef;
  padding: 10px 12px;
}
:global(.pdf-report td:nth-child(5)) {
  text-align: right;
}

@media (max-width: 920px) {
  .filter-panel {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .btn-reset {
    grid-column: span 2;
  }

  .search-field {
    grid-column: span 2;
  }
}

@media (max-width: 640px) {
  .fm-container {
    padding: 1.5rem 0.9rem 2rem;
  }

  .card-toolbar,
  .dialog-footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .filter-panel {
    grid-template-columns: 1fr;
  }

  .btn-reset {
    grid-column: auto;
  }
}
</style>
