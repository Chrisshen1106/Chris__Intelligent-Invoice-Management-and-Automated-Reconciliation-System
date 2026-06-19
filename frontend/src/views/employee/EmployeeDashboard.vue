<template>
  <div class="system-container">
    <div class="system-block">
      <div class="dashboard-header">
        <button
          @click="handleNewApplication"
          :class="['nav-btn', { active: activeTab === 'ocr' }]"
        >
          <span class="icon">➕</span> {{ $t('employee.new_application') }}
        </button>
        <div class="status-group">
          <button
            @click="handleViewRecords('submitted')"
            :class="['nav-btn', { active: activeTab === 'submitted' }]"
          >
            {{ $t('employee.view_submitted_records') }}
          </button>
          <button
            @click="handleViewRecords('rejected')"
            :class="['nav-btn', { active: activeTab === 'rejected' }]"
          >
            {{ $t('employee.view_rejected_records') }}
          </button>
        </div>
      </div>

      <div class="dashboard-content">
        <transition name="slide-fade" mode="out-in">
          <div v-if="activeTab === 'ocr'" class="section-card" key="ocr-upload">
            <h2 class="section-title">{{ $t('employee.upload_document') }}</h2>

            <div class="step-box">
              <h3 class="step-title">{{ $t('employee.step1_ocr') }}</h3>

              <div class="form-group">
                <label>{{ $t('employee.doc_type') }}</label>
                <select v-model="docType" class="doc-type-select">
                  <option value="invoice">{{ $t('employee.doc_type_invoice') }}</option>
                  <option value="purchaseOrder">{{ $t('employee.doc_type_purchase_order') }}</option>
                  <option value="goodsReceipt">{{ $t('employee.doc_type_goods_receipt') }}</option>
                </select>
              </div>

              <div class="form-group">
                <label>{{ $t('employee.upload_document') }}</label>
                <div
                  class="file-drop-zone"
                  :class="{ 'file-drop-zone--active': isDragging, 'file-drop-zone--has-file': uploadFile }"
                  @click="$refs.fileInput.click()"
                  @dragover.prevent="isDragging = true"
                  @dragleave.prevent="isDragging = false"
                  @drop.prevent="handleDrop"
                >
                  <input
                    ref="fileInput"
                    type="file"
                    @change="handleFileUpload"
                    accept="application/pdf,image/*"
                    class="file-input-hidden"
                  />
                  <div v-if="!uploadFile" class="file-drop-content">
                    <svg class="file-drop-icon" viewBox="0 0 48 48" fill="none">
                      <rect x="8" y="14" width="32" height="26" rx="4" stroke="currentColor" stroke-width="2.5" fill="none"/>
                      <path d="M24 10v18M17 21l7-7 7 7" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <p class="file-drop-text">{{ $t('employee.drop_or_click') }}</p>
                    <span class="file-drop-hint">{{ $t('employee.file_type') }}</span>
                  </div>
                  <div v-else class="file-drop-content file-drop-done">
                    <svg class="file-drop-icon file-drop-icon--ok" viewBox="0 0 48 48" fill="none">
                      <circle cx="24" cy="24" r="18" stroke="currentColor" stroke-width="2.5" fill="none"/>
                      <path d="M15 25l6 6 12-12" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <p class="file-drop-text">{{ uploadFile.name }}</p>
                    <span class="file-drop-hint">{{ $t('employee.click_to_change') }}</span>
                  </div>
                </div>
              </div>
              <div class="form-actions">
                <button
                  type="button"
                  class="btn-primary"
                  :disabled="!uploadFile || ocrSubmitting"
                  @click="handleRunOcr"
                >
                  {{ ocrSubmitting ? $t('employee.ocr_queueing') : $t('employee.queue_ocr') }}
                </button>
              </div>
            </div>

            <div class="ocr-queue-panel">
              <div class="ocr-queue-header">
                <h3 class="step-title">{{ $t('employee.ocr_queue_title') }}</h3>
                <div class="ocr-queue-stats">
                  <span>{{ $t('employee.ocr_queue_active') }} {{ activeOcrJobCount }}</span>
                  <span>{{ $t('employee.ocr_queue_ready') }} {{ completedOcrJobCount }}</span>
                </div>
              </div>
              <div v-if="ocrJobs.length" class="ocr-job-list">
                <div v-for="job in ocrJobs" :key="job.localId" class="ocr-job-row">
                  <div class="ocr-job-main">
                    <span class="ocr-job-doc">{{ $t(docTypeLabelKey(job.documentType)) }}</span>
                    <span class="ocr-job-file">{{ job.filename }}</span>
                  </div>
                  <span :class="['ocr-job-badge', `ocr-job-badge--${job.status}`]">
                    {{ $t(`employee.ocr_status_${job.status}`) }}
                  </span>
                  <button
                    v-if="job.status === 'completed'"
                    type="button"
                    class="btn-ghost btn-small"
                    @click="applyOcrJob(job)"
                  >
                    {{ $t('employee.apply_ocr_result') }}
                  </button>
                  <button
                    v-else-if="job.status === 'failed'"
                    type="button"
                    class="btn-ghost btn-small"
                    @click="retryOcrJob(job)"
                  >
                    {{ $t('employee.retry_ocr') }}
                  </button>
                </div>
              </div>
              <div v-else class="ocr-queue-empty">
                {{ $t('employee.ocr_queue_empty') }}
              </div>
            </div>

            <div v-if="hasOcrDraft && uploadFile" class="file-preview-box">
              <h3 class="step-title">{{ $t('employee.file_preview') }}</h3>
              <div v-if="isImageFile(uploadFile)" class="file-preview-img">
                <img :src="filePreviewUrl" alt="preview" style="max-width:100%;max-height:400px;border:1px solid #eee;border-radius:8px;" />
              </div>
              <div v-else-if="isPdfFile(uploadFile)" class="file-preview-pdf">
                <embed :src="filePreviewUrl" type="application/pdf" width="100%" height="400px" style="border:1px solid #eee;border-radius:8px;" />
              </div>
              <div v-else class="file-preview-unsupported">
                <span>{{ $t('employee.unsupported_preview') }}</span>
              </div>
            </div>

            <div v-if="hasOcrDraft && docType === 'invoice'" class="step-box">
              <h3 class="step-title">{{ $t('employee.step2_confirm') }}</h3>
              <form @submit.prevent="handleSubmit" class="application-form">
                <div class="form-group">
                  <label>{{ $t('employee.invoiceNo') }}</label>
                  <input type="text" v-model="invoiceDraft.invoiceNo" required />
                </div>
                <div class="form-group full-width">
                  <label>{{ $t('employee.select_po_no') }}</label>
                  <div class="po-dropdown" :class="{ 'po-dropdown--open': poDropdownOpen }" ref="poDropdown">
                    <div class="po-dropdown-trigger" @click="togglePoDropdown" tabindex="0" @keydown.enter.prevent="togglePoDropdown" @keydown.space.prevent="togglePoDropdown">
                      <span class="po-dropdown-value" :class="{ 'po-dropdown-placeholder': !invoiceDraft.poNo }">
                        {{ invoiceDraft.poNo ? (approvedPos.find(p => p.poNo === invoiceDraft.poNo) ? invoiceDraft.poNo + ' - ' + approvedPos.find(p => p.poNo === invoiceDraft.poNo).vendorName : invoiceDraft.poNo) : $t('employee.po_no_required') }}
                      </span>
                      <span class="po-dropdown-arrow">▾</span>
                    </div>
                    <div v-if="poDropdownOpen" class="po-dropdown-panel">
                      <div class="po-dropdown-search-wrap">
                        <input
                          type="text"
                          v-model="poSearch"
                          class="po-dropdown-search"
                          :placeholder="$t('employee.po_search_placeholder')"
                          @click.stop
                          ref="poSearchInput"
                        />
                        <button type="button" class="po-refresh-btn" :disabled="poLoading" @click.stop="loadApprovedPos(true)" :title="$t('employee.refresh_po_list')">⟳</button>
                      </div>
                      <ul class="po-dropdown-list">
                        <li v-if="filteredApprovedPos.length === 0" class="po-dropdown-empty">{{ $t('employee.no_po_found') }}</li>
                        <li
                          v-for="po in filteredApprovedPos"
                          :key="po.poNo"
                          class="po-dropdown-item"
                          :class="{ 'po-dropdown-item--selected': invoiceDraft.poNo === po.poNo }"
                          @click="selectPo(po, 'invoice')"
                        >
                          <span class="po-item-no">{{ po.poNo }}</span>
                          <span class="po-item-meta">{{ po.vendorName }} · {{ po.poDate }}</span>
                        </li>
                      </ul>
                    </div>
                  </div>
                  <p v-if="poWarning" class="helper-text warning-text">{{ poWarning }}</p>
                  <p v-if="poError" class="helper-text error-text">{{ poError }}</p>
                </div>
                <div class="form-group">
                  <label>{{ $t('employee.reimbursement_date') }}</label>
                  <input type="date" v-model="invoiceDraft.invoiceDate" required />
                </div>
                <div class="form-group">
                  <label>{{ $t('employee.col_vendor') }}</label>
                  <input type="text" v-model="invoiceDraft.vendorName" required />
                </div>
                <div class="form-group">
                  <label>{{ $t('employee.tax_id') }}</label>
                  <input type="text" v-model="invoiceDraft.taxId" required />
                </div>
                <div class="form-group full-width">
                  <label>{{ $t('employee.reimbursement_amount') }}</label>
                  <div class="amount-input">
                    <span class="currency">$</span>
                    <input type="number" min="0" v-model.number="invoiceDraft.totalAmount" required />
                  </div>
                </div>
                <div class="full-width">
                  <h4 class="items-title">{{ $t('employee.detailed_items') }}</h4>
                  <div class="item-row item-header-row">
                    <span>{{ $t('employee.item_name') }}</span>
                    <span>{{ $t('employee.quantity') }}</span>
                    <span>{{ $t('employee.unit_price') }}</span>
                  </div>
                  <div v-for="(item, index) in invoiceDraft.items" :key="index">
                    <div class="item-row">
                      <input type="text" v-model="item.itemName" :placeholder="$t('employee.item_name')" required />
                      <input type="number" min="0" v-model.number="item.quantity" :placeholder="$t('employee.quantity')" required />
                      <input type="number" min="0" v-model.number="item.unitPrice" :placeholder="$t('employee.unit_price')" required />
                    </div>
                    <div class="item-row-actions" v-if="invoiceDraft.items.length > 1">
                      <button type="button" class="btn-ghost btn-small" @click="removeInvoiceItem(index)">
                        {{ $t('employee.remove_item') }}
                      </button>
                    </div>
                  </div>
                  <div class="item-add">
                    <button type="button" class="btn-ghost btn-small" @click="addInvoiceItem">
                      {{ $t('employee.add_item') }}
                    </button>
                  </div>
                </div>
                <div class="form-actions full-width">
                  <button type="submit" class="btn-primary" :disabled="submitLoading">
                    {{ submitLoading ? $t('employee.submitting') : $t('employee.submit') }}
                  </button>
                </div>
              </form>
            </div>

            <div v-if="hasOcrDraft && docType === 'purchaseOrder'" class="step-box">
              <h3 class="step-title">{{ $t('employee.step2_confirm_purchase_order') }}</h3>
              <form @submit.prevent="handleSubmit" class="application-form">
                <div class="form-group">
                  <label>{{ $t('employee.po_number') }}</label>
                  <input type="text" v-model="poDraft.poNo" required />
                </div>
                <div class="form-group">
                  <label>{{ $t('employee.purchaser') }}</label>
                  <input type="text" v-model="poDraft.purchaser" required />
                </div>
                <div class="form-group">
                  <label>{{ $t('employee.department') }}</label>
                  <input type="text" v-model="poDraft.department" required />
                </div>
                <div class="form-group">
                  <label>{{ $t('employee.vendor_name') }}</label>
                  <input type="text" v-model="poDraft.vendorName" required />
                </div>
                <div class="form-group">
                  <label>{{ $t('employee.tax_id') }}</label>
                  <input type="text" v-model="poDraft.taxId" />
                </div>
                <div class="form-group">
                  <label>{{ $t('employee.order_date') }}</label>
                  <input type="date" v-model="poDraft.poDate" required />
                </div>
                <div class="form-group full-width">
                  <label>{{ $t('employee.total_amount') }}</label>
                  <div class="amount-input">
                    <span class="currency">$</span>
                    <input type="number" min="0" v-model.number="poDraft.totalAmount" required />
                  </div>
                </div>
                <div class="full-width">
                  <h4 class="items-title">{{ $t('employee.detailed_items') }}</h4>
                  <div class="item-row item-row-5 item-header-row">
                    <span>{{ $t('employee.item_name') }}</span>
                    <span>{{ $t('employee.spec') }}</span>
                    <span>{{ $t('employee.quantity') }}</span>
                    <span>{{ $t('employee.unit_price') }}</span>
                    <span>{{ $t('employee.line_amount') }}</span>
                  </div>
                  <div v-for="(item, index) in poDraft.items" :key="index">
                    <div class="item-row item-row-5">
                      <input type="text" v-model="item.itemName" :placeholder="$t('employee.item_name')" required />
                      <input type="text" v-model="item.spec" :placeholder="$t('employee.spec')" />
                      <input type="number" min="0" v-model.number="item.quantity" :placeholder="$t('employee.quantity')" required />
                      <input type="number" min="0" v-model.number="item.unitPrice" :placeholder="$t('employee.unit_price')" required />
                      <input type="number" min="0" v-model.number="item.lineAmount" :placeholder="$t('employee.line_amount')" required />
                    </div>
                    <div class="item-row-actions" v-if="poDraft.items.length > 1">
                      <button type="button" class="btn-ghost btn-small" @click="removePoItem(index)">
                        {{ $t('employee.remove_item') }}
                      </button>
                    </div>
                  </div>
                  <div class="item-add">
                    <button type="button" class="btn-ghost btn-small" @click="addPoItem">
                      {{ $t('employee.add_item') }}
                    </button>
                  </div>
                </div>
                <div class="form-actions full-width">
                  <button type="submit" class="btn-primary" :disabled="submitLoading">
                    {{ submitLoading ? $t('employee.submitting') : $t('employee.submit') }}
                  </button>
                </div>
              </form>
            </div>

            <div v-if="hasOcrDraft && docType === 'goodsReceipt'" class="step-box">
              <h3 class="step-title">{{ $t('employee.step2_confirm_goods_receipt') }}</h3>
              <form @submit.prevent="handleSubmit" class="application-form">
                <div class="form-group">
                  <label>{{ $t('employee.gr_no') }}</label>
                  <input type="text" v-model="grDraft.grNo" required />
                </div>
                <div class="form-group full-width">
                  <label>{{ $t('employee.select_po_no') }}</label>
                  <div class="po-dropdown" :class="{ 'po-dropdown--open': grPoDropdownOpen }" ref="grPoDropdown">
                    <div class="po-dropdown-trigger" @click="toggleGrPoDropdown" tabindex="0" @keydown.enter.prevent="toggleGrPoDropdown" @keydown.space.prevent="toggleGrPoDropdown">
                      <span class="po-dropdown-value" :class="{ 'po-dropdown-placeholder': !grDraft.poNo }">
                        {{ grDraft.poNo ? (approvedPos.find(p => p.poNo === grDraft.poNo) ? grDraft.poNo + ' - ' + approvedPos.find(p => p.poNo === grDraft.poNo).vendorName : grDraft.poNo) : $t('employee.po_no_required') }}
                      </span>
                      <span class="po-dropdown-arrow">▾</span>
                    </div>
                    <div v-if="grPoDropdownOpen" class="po-dropdown-panel">
                      <div class="po-dropdown-search-wrap">
                        <input
                          type="text"
                          v-model="poSearch"
                          class="po-dropdown-search"
                          :placeholder="$t('employee.po_search_placeholder')"
                          @click.stop
                          ref="grPoSearchInput"
                        />
                        <button type="button" class="po-refresh-btn" :disabled="poLoading" @click.stop="loadApprovedPos(true)" :title="$t('employee.refresh_po_list')">⟳</button>
                      </div>
                      <ul class="po-dropdown-list">
                        <li v-if="filteredApprovedPos.length === 0" class="po-dropdown-empty">{{ $t('employee.no_po_found') }}</li>
                        <li
                          v-for="po in filteredApprovedPos"
                          :key="po.poNo"
                          class="po-dropdown-item"
                          :class="{ 'po-dropdown-item--selected': grDraft.poNo === po.poNo }"
                          @click="selectPo(po, 'gr')"
                        >
                          <span class="po-item-no">{{ po.poNo }}</span>
                          <span class="po-item-meta">{{ po.vendorName }} · {{ po.poDate }}</span>
                        </li>
                      </ul>
                    </div>
                  </div>
                  <p v-if="poWarning" class="helper-text warning-text">{{ poWarning }}</p>
                  <p v-if="poError" class="helper-text error-text">{{ poError }}</p>
                </div>
                <div class="form-group">
                  <label>{{ $t('employee.applicant') }}</label>
                  <input type="text" v-model="grDraft.applicant" required />
                </div>
                <div class="form-group">
                  <label>{{ $t('employee.receiver') }}</label>
                  <input type="text" v-model="grDraft.receiver" required />
                </div>
                <div class="form-group">
                  <label>{{ $t('employee.receipt_date') }}</label>
                  <input type="date" v-model="grDraft.grDate" required />
                </div>
                <div class="form-group">
                  <label>{{ $t('employee.total_qty') }}</label>
                  <input type="number" min="0" v-model.number="grDraft.totalQty" required />
                </div>
                <div class="form-group">
                  <label>{{ $t('employee.total_amount') }}</label>
                  <div class="amount-input">
                    <span class="currency">$</span>
                    <input type="number" min="0" v-model.number="grDraft.totalAmount" required />
                  </div>
                </div>
                <div class="full-width">
                  <h4 class="items-title">{{ $t('employee.detailed_items') }}</h4>
                  <div class="item-row item-row-4 item-header-row">
                    <span>{{ $t('employee.item_name') }}</span>
                    <span>{{ $t('employee.received_qty') }}</span>
                    <span>{{ $t('employee.accepted_qty') }}</span>
                    <span>{{ $t('employee.line_amount') }}</span>
                  </div>
                  <div v-for="(item, index) in grDraft.items" :key="index">
                    <div class="item-row item-row-4">
                      <input type="text" v-model="item.itemName" :placeholder="$t('employee.item_name')" required />
                      <input type="number" min="0" v-model.number="item.receivedQty" :placeholder="$t('employee.received_qty')" required />
                      <input type="number" min="0" v-model.number="item.acceptedQty" :placeholder="$t('employee.accepted_qty')" required />
                      <input type="number" min="0" v-model.number="item.lineAmount" :placeholder="$t('employee.line_amount')" required />
                    </div>
                    <div class="item-row-actions" v-if="grDraft.items.length > 1">
                      <button type="button" class="btn-ghost btn-small" @click="removeGrItem(index)">
                        {{ $t('employee.remove_item') }}
                      </button>
                    </div>
                  </div>
                  <div class="item-add">
                    <button type="button" class="btn-ghost btn-small" @click="addGrItem">
                      {{ $t('employee.add_item') }}
                    </button>
                  </div>
                </div>
                <div class="form-actions full-width">
                  <button type="submit" class="btn-primary" :disabled="submitLoading">
                    {{ submitLoading ? $t('employee.submitting') : $t('employee.submit') }}
                  </button>
                </div>
              </form>
            </div>

            <p v-if="apiError" class="error-text">{{ apiError }}</p>
            <p v-if="submitMessage" class="success-text">{{ $t(submitMessage) }}</p>
          </div>

          <div v-else-if="activeTab === 'submitted'" class="section-card" key="submitted-table">
            <h2 class="section-title">{{ $t('employee.view_submitted_records') }}</h2>
            <div class="table-responsive">
              <table class="modern-table">
                <thead>
                  <tr>
                    <th>{{ $t('employee.doc_type') }}</th>
                    <th>{{ $t('employee.doc_no') }}</th>
                    <th>{{ $t('employee.total_amount') }}</th>
                    <th>{{ $t('employee.submitted_time') }}</th>
                    <th>{{ $t('employee.current_progress') }}</th>
                    <th>{{ $t('employee.actions') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="record in submittedRecords" :key="record.docId">
                    <td>{{ $t(docTypeLabelKey(record.docType)) }}</td>
                    <td class="text-bold">{{ record.docNo }}</td>
                    <td>${{ record.totalAmount }}</td>
                    <td>{{ record.submittedAt }}</td>
                    <td>
                      <span :class="'status-badge status-' + formatStatus(record.status)">{{ $t('employee.status_' + formatStatus(record.status)) }}</span>
                    </td>
                    <td>
                      <button type="button" class="btn-ghost btn-small" @click="loadDocumentDetail(record.docId)">
                        {{ $t('employee.view_detail') }}
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-if="submittedLoading" class="empty-state">{{ $t('employee.loading') }}</div>
              <div v-else-if="submittedRecords.length === 0" class="empty-state">
                {{ $t('employee.no_submitted_records') }}
              </div>
              <p v-if="submittedError" class="error-text">{{ submittedError }}</p>
            </div>

            <div v-if="detailLoading" class="empty-state">{{ $t('employee.loading') }}</div>
            <div v-if="selectedDocDetail" class="detail-panel">
              <div class="detail-header">
                <h3 class="detail-title">{{ $t('employee.detail_title') }}</h3>
                <button type="button" class="btn-ghost btn-small" @click="clearDocumentDetail">
                  {{ $t('employee.close_detail') }}
                </button>
              </div>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.doc_type') }}</span>
                  <span class="detail-value">{{ $t(docTypeLabelKey(selectedDocDetail.docType)) }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.doc_no') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.docNo }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.total_amount') }}</span>
                  <span class="detail-value">${{ selectedDocDetail.totalAmount }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.submitted_time') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.submittedAt }}</span>
                </div>
              </div>

              <div v-if="selectedDocDetail.docType === 'invoice'" class="detail-grid">
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.invoiceNo') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.formData?.invoiceNo }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.col_po_no') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.formData?.poNo }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.reimbursement_date') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.formData?.invoiceDate }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.col_vendor') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.formData?.vendorName }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.tax_id') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.formData?.taxId }}</span>
                </div>
              </div>

              <div v-else-if="selectedDocDetail.docType === 'purchaseOrder'" class="detail-grid">
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.po_number') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.formData?.poNo }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.purchaser') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.formData?.purchaser }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.department') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.formData?.department }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.vendor_name') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.formData?.vendorName }}</span>
                </div>
              </div>

              <div v-else-if="selectedDocDetail.docType === 'goodsReceipt'" class="detail-grid">
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.gr_no') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.formData?.grNo }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.col_po_no') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.formData?.poNo }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.applicant') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.formData?.applicant }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.receipt_date') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.formData?.grDate }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">{{ $t('employee.total_qty') }}</span>
                  <span class="detail-value">{{ selectedDocDetail.formData?.totalQty }}</span>
                </div>
              </div>

              <div class="detail-actions">
                <button
                  type="button"
                  class="btn-ghost btn-small"
                  :disabled="detailFileLoading"
                  @click="previewDocumentFile(selectedDocDetail.docId)"
                >
                  {{ detailFileLoading ? $t('employee.preview_loading') : $t('employee.preview_file') }}
                </button>
                <button
                  v-if="['pending', 'pendingMatch', 'rejected'].includes(selectedDocDetail.status)"
                  type="button"
                  class="btn-danger btn-small"
                  :disabled="voidLoading"
                  @click="handleVoidDocument(selectedDocDetail.docId)"
                >
                  {{ voidLoading ? $t('employee.voiding') : $t('employee.void_document') }}
                </button>
              </div>

              <div v-if="detailFileUrl" class="file-preview-box">
                <h3 class="step-title">{{ $t('employee.file_preview') }}</h3>
                <div v-if="isImageMime(detailFileType)" class="file-preview-img">
                  <img :src="detailFileUrl" alt="preview" style="max-width:100%;max-height:400px;border:1px solid #eee;border-radius:8px;" />
                </div>
                <div v-else-if="isPdfMime(detailFileType)" class="file-preview-pdf">
                  <embed :src="detailFileUrl" type="application/pdf" width="100%" height="400px" style="border:1px solid #eee;border-radius:8px;" />
                </div>
                <div v-else class="file-preview-unsupported">
                  <span>{{ $t('employee.unsupported_preview') }}</span>
                </div>
              </div>

              <div class="detail-items">
                <h4 class="items-title">{{ $t('employee.detailed_items') }}</h4>
                <table class="modern-table detail-table" v-if="selectedDocDetail.items?.length">
                  <thead v-if="selectedDocDetail.docType === 'invoice'">
                    <tr>
                      <th>{{ $t('employee.item_name') }}</th>
                      <th>{{ $t('employee.quantity') }}</th>
                      <th>{{ $t('employee.unit_price') }}</th>
                    </tr>
                  </thead>
                  <thead v-else-if="selectedDocDetail.docType === 'purchaseOrder'">
                    <tr>
                      <th>{{ $t('employee.item_name') }}</th>
                      <th>{{ $t('employee.spec') }}</th>
                      <th>{{ $t('employee.quantity') }}</th>
                      <th>{{ $t('employee.unit_price') }}</th>
                      <th>{{ $t('employee.line_amount') }}</th>
                    </tr>
                  </thead>
                  <thead v-else-if="selectedDocDetail.docType === 'goodsReceipt'">
                    <tr>
                      <th>{{ $t('employee.item_name') }}</th>
                      <th>{{ $t('employee.received_qty') }}</th>
                      <th>{{ $t('employee.accepted_qty') }}</th>
                      <th>{{ $t('employee.line_amount') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, index) in selectedDocDetail.items" :key="index">
                      <template v-if="selectedDocDetail.docType === 'invoice'">
                        <td>{{ item.itemName }}</td>
                        <td>{{ item.quantity }}</td>
                        <td>{{ item.unitPrice }}</td>
                      </template>
                      <template v-else-if="selectedDocDetail.docType === 'purchaseOrder'">
                        <td>{{ item.itemName }}</td>
                        <td>{{ item.spec }}</td>
                        <td>{{ item.quantity }}</td>
                        <td>{{ item.unitPrice }}</td>
                        <td>{{ item.lineAmount }}</td>
                      </template>
                      <template v-else-if="selectedDocDetail.docType === 'goodsReceipt'">
                        <td>{{ item.itemName }}</td>
                        <td>{{ item.receivedQty }}</td>
                        <td>{{ item.acceptedQty }}</td>
                        <td>{{ item.lineAmount }}</td>
                      </template>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p v-if="detailError" class="error-text">{{ detailError }}</p>
            </div>
            <p v-if="detailError && !selectedDocDetail" class="error-text">{{ detailError }}</p>
          </div>

          <div v-else-if="activeTab === 'rejected'" class="section-card" key="rejected-table">
            <h2 class="section-title">{{ $t('employee.view_rejected_records') }}</h2>
            <div class="table-responsive">
              <table class="modern-table">
                <thead>
                  <tr>
                    <th>{{ $t('employee.doc_type') }}</th>
                    <th>{{ $t('employee.doc_no') }}</th>
                    <th>{{ $t('employee.col_vendor') }}</th>
                    <th>{{ $t('employee.col_po_no') }}</th>
                    <th>{{ $t('employee.reject_reason') }}</th>
                    <th>{{ $t('employee.rejected_at') }}</th>
                    <th>{{ $t('employee.actions') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="record in rejectedRecords" :key="record.docId || record.docNo || record.invoiceNo">
                    <td>{{ record.docType ? $t(docTypeLabelKey(record.docType)) : '-' }}</td>
                    <td class="text-bold">{{ record.docNo || record.invoiceNo || '-' }}</td>
                    <td>{{ record.vendorName || '-' }}</td>
                    <td>{{ record.poNo || '-' }}</td>
                    <td>{{ record.rejectReason || '-' }}</td>
                    <td>{{ record.rejectedAt || '-' }}</td>
                    <td>
                      <button
                        type="button"
                        class="btn-ghost btn-small"
                        @click="openRejectedModal(record)"
                      >
                        {{ $t('employee.edit') }}
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-if="rejectedLoading" class="empty-state">{{ $t('employee.loading') }}</div>
              <div v-else-if="rejectedRecords.length === 0" class="empty-state">
                {{ $t('employee.no_records') }}
              </div>
              <p v-if="rejectedError" class="error-text">{{ rejectedError }}</p>
            </div>
          </div>
        </transition>
      </div>
    </div>

    <div v-if="rejectedModalOpen" class="modal-backdrop">
      <div class="modal-card">
        <div class="modal-header">
          <h3 class="modal-title">{{ $t(`employee.rejected_edit_title_${rejectedDocType}`) }}</h3>
          <button type="button" class="btn-ghost btn-small" @click="closeRejectedModal">
            {{ $t('employee.close_detail') }}
          </button>
        </div>
        <form @submit.prevent="handleRejectedResubmit" class="modal-body application-form">
          <!-- Invoice Fields -->
          <template v-if="rejectedDocType === 'invoice'">
            <div class="form-group">
              <label>{{ $t('employee.invoiceNo') }}</label>
              <input type="text" v-model="rejectedDraft.invoiceNo" readonly />
            </div>
            <div class="form-group full-width">
              <label>{{ $t('employee.select_po_no') }}</label>
              <div class="po-dropdown" :class="{ 'po-dropdown--open': rejectedPoDropdownOpen }" ref="rejectedPoDropdown">
                <div class="po-dropdown-trigger" @click="toggleRejectedPoDropdown" tabindex="0" @keydown.enter.prevent="toggleRejectedPoDropdown" @keydown.space.prevent="toggleRejectedPoDropdown">
                  <span class="po-dropdown-value" :class="{ 'po-dropdown-placeholder': !rejectedDraft.poNo }">
                    {{ rejectedDraft.poNo ? (approvedPos.find(p => p.poNo === rejectedDraft.poNo) ? rejectedDraft.poNo + ' - ' + approvedPos.find(p => p.poNo === rejectedDraft.poNo).vendorName : rejectedDraft.poNo) : $t('employee.po_no_required') }}
                  </span>
                  <span class="po-dropdown-arrow">▾</span>
                </div>
                <div v-if="rejectedPoDropdownOpen" class="po-dropdown-panel">
                  <div class="po-dropdown-search-wrap">
                    <input
                      type="text"
                      v-model="rejectedPoSearch"
                      class="po-dropdown-search"
                      :placeholder="$t('employee.po_search_placeholder')"
                      @click.stop
                      ref="rejectedPoSearchInput"
                    />
                    <button type="button" class="po-refresh-btn" :disabled="poLoading" @click.stop="loadApprovedPos(true)" :title="$t('employee.refresh_po_list')">⟳</button>
                  </div>
                  <ul class="po-dropdown-list">
                    <li v-if="filteredRejectedPos.length === 0" class="po-dropdown-empty">{{ $t('employee.no_po_found') }}</li>
                    <li
                      v-for="po in filteredRejectedPos"
                      :key="po.poNo"
                      class="po-dropdown-item"
                      :class="{ 'po-dropdown-item--selected': rejectedDraft.poNo === po.poNo }"
                      @click="selectPo(po, 'rejected')"
                    >
                      <span class="po-item-no">{{ po.poNo }}</span>
                      <span class="po-item-meta">{{ po.vendorName }} · {{ po.poDate }}</span>
                    </li>
                  </ul>
                </div>
              </div>
              <p v-if="rejectedPoWarning" class="helper-text warning-text">{{ rejectedPoWarning }}</p>
              <p v-if="poError" class="helper-text error-text">{{ poError }}</p>
            </div>
            <div class="form-group">
              <label>{{ $t('employee.reimbursement_date') }}</label>
              <input type="date" v-model="rejectedDraft.invoiceDate" required />
            </div>
            <div class="form-group">
              <label>{{ $t('employee.col_vendor') }}</label>
              <input type="text" v-model="rejectedDraft.vendorName" required />
            </div>
            <div class="form-group">
              <label>{{ $t('employee.tax_id') }}</label>
              <input type="text" v-model="rejectedDraft.taxId" required />
            </div>
            <div class="form-group full-width">
              <label>{{ $t('employee.reimbursement_amount') }}</label>
              <div class="amount-input">
                <span class="currency">$</span>
                <input type="number" min="0" v-model.number="rejectedDraft.totalAmount" required />
              </div>
            </div>
          </template>

          <!-- Purchase Order Fields -->
          <template v-else-if="rejectedDocType === 'purchaseOrder'">
            <div class="form-group">
              <label>{{ $t('employee.po_number') }}</label>
              <input type="text" v-model="rejectedDraft.poNo" readonly />
            </div>
            <div class="form-group">
              <label>{{ $t('employee.purchaser') }}</label>
              <input type="text" v-model="rejectedDraft.purchaser" required />
            </div>
            <div class="form-group">
              <label>{{ $t('employee.department') }}</label>
              <input type="text" v-model="rejectedDraft.department" required />
            </div>
            <div class="form-group">
              <label>{{ $t('employee.vendor_name') }}</label>
              <input type="text" v-model="rejectedDraft.vendorName" required />
            </div>
            <div class="form-group">
              <label>{{ $t('employee.tax_id') }}</label>
              <input type="text" v-model="rejectedDraft.taxId" />
            </div>
            <div class="form-group">
              <label>{{ $t('employee.order_date') }}</label>
              <input type="date" v-model="rejectedDraft.poDate" required />
            </div>
            <div class="form-group full-width">
              <label>{{ $t('employee.total_amount') }}</label>
              <div class="amount-input">
                <span class="currency">$</span>
                <input type="number" min="0" v-model.number="rejectedDraft.totalAmount" required />
              </div>
            </div>
          </template>

          <!-- Goods Receipt Fields -->
          <template v-else-if="rejectedDocType === 'goodsReceipt'">
            <div class="form-group">
              <label>{{ $t('employee.gr_no') }}</label>
              <input type="text" v-model="rejectedDraft.grNo" readonly />
            </div>
            <div class="form-group full-width">
              <label>{{ $t('employee.select_po_no') }}</label>
              <div class="po-dropdown" :class="{ 'po-dropdown--open': rejectedPoDropdownOpen }" ref="rejectedPoDropdown">
                <div class="po-dropdown-trigger" @click="toggleRejectedPoDropdown" tabindex="0" @keydown.enter.prevent="toggleRejectedPoDropdown" @keydown.space.prevent="toggleRejectedPoDropdown">
                  <span class="po-dropdown-value" :class="{ 'po-dropdown-placeholder': !rejectedDraft.poNo }">
                    {{ rejectedDraft.poNo ? (approvedPos.find(p => p.poNo === rejectedDraft.poNo) ? rejectedDraft.poNo + ' - ' + approvedPos.find(p => p.poNo === rejectedDraft.poNo).vendorName : rejectedDraft.poNo) : $t('employee.po_no_required') }}
                  </span>
                  <span class="po-dropdown-arrow">▾</span>
                </div>
                <div v-if="rejectedPoDropdownOpen" class="po-dropdown-panel">
                  <div class="po-dropdown-search-wrap">
                    <input
                      type="text"
                      v-model="rejectedPoSearch"
                      class="po-dropdown-search"
                      :placeholder="$t('employee.po_search_placeholder')"
                      @click.stop
                      ref="rejectedPoSearchInput"
                    />
                    <button type="button" class="po-refresh-btn" :disabled="poLoading" @click.stop="loadApprovedPos(true)" :title="$t('employee.refresh_po_list')">⟳</button>
                  </div>
                  <ul class="po-dropdown-list">
                    <li v-if="filteredRejectedPos.length === 0" class="po-dropdown-empty">{{ $t('employee.no_po_found') }}</li>
                    <li
                      v-for="po in filteredRejectedPos"
                      :key="po.poNo"
                      class="po-dropdown-item"
                      :class="{ 'po-dropdown-item--selected': rejectedDraft.poNo === po.poNo }"
                      @click="selectPo(po, 'rejected')"
                    >
                      <span class="po-item-no">{{ po.poNo }}</span>
                      <span class="po-item-meta">{{ po.vendorName }} · {{ po.poDate }}</span>
                    </li>
                  </ul>
                </div>
              </div>
              <p v-if="rejectedPoWarning" class="helper-text warning-text">{{ rejectedPoWarning }}</p>
              <p v-if="poError" class="helper-text error-text">{{ poError }}</p>
            </div>
            <div class="form-group">
              <label>{{ $t('employee.applicant') }}</label>
              <input type="text" v-model="rejectedDraft.applicant" required />
            </div>
            <div class="form-group">
              <label>{{ $t('employee.receiver') }}</label>
              <input type="text" v-model="rejectedDraft.receiver" required />
            </div>
            <div class="form-group">
              <label>{{ $t('employee.receipt_date') }}</label>
              <input type="date" v-model="rejectedDraft.grDate" required />
            </div>
            <div class="form-group">
              <label>{{ $t('employee.total_qty') }}</label>
              <input type="number" min="0" v-model.number="rejectedDraft.totalQty" required />
            </div>
            <div class="form-group">
              <label>{{ $t('employee.total_amount') }}</label>
              <div class="amount-input">
                <span class="currency">$</span>
                <input type="number" min="0" v-model.number="rejectedDraft.totalAmount" required />
              </div>
            </div>
          </template>

          <div class="form-group full-width">
            <label>{{ $t('employee.upload_document') }}</label>
            <div class="file-input-row">
              <input type="file" @change="handleRejectedFileChange" accept="application/pdf,image/*" />
              <button
                type="button"
                class="btn-ghost btn-small"
                :disabled="!rejectedFile || rejectedOcrSubmitting"
                @click="handleRejectedOcr"
              >
                {{ $t('employee.run_ocr') }}
              </button>
            </div>
            <p v-if="rejectedOcrSubmitting" class="helper-text">{{ $t('employee.ocr_processing') }}</p>
          </div>
          <div v-if="rejectedPreviewUrl" class="file-preview-box full-width">
            <h3 class="step-title">{{ $t('employee.file_preview') }}</h3>
            <div v-if="rejectedPreviewIsImage" class="file-preview-img">
              <img :src="rejectedPreviewUrl" alt="preview" style="max-width:100%;max-height:400px;border:1px solid #eee;border-radius:8px;" />
            </div>
            <div v-else-if="rejectedPreviewIsPdf" class="file-preview-pdf">
              <embed :src="rejectedPreviewUrl" type="application/pdf" width="100%" height="400px" style="border:1px solid #eee;border-radius:8px;" />
            </div>
            <div v-else class="file-preview-unsupported">
              <span>{{ $t('employee.unsupported_preview') }}</span>
            </div>
          </div>

          <div class="full-width">
            <h4 class="items-title">{{ $t('employee.detailed_items') }}</h4>
            <div v-if="rejectedDocType === 'invoice'" class="item-row item-header-row">
              <span>{{ $t('employee.item_name') }}</span>
              <span>{{ $t('employee.quantity') }}</span>
              <span>{{ $t('employee.unit_price') }}</span>
            </div>
            <div v-else-if="rejectedDocType === 'purchaseOrder'" class="item-row item-row-5 item-header-row">
              <span>{{ $t('employee.item_name') }}</span>
              <span>{{ $t('employee.spec') }}</span>
              <span>{{ $t('employee.quantity') }}</span>
              <span>{{ $t('employee.unit_price') }}</span>
              <span>{{ $t('employee.line_amount') }}</span>
            </div>
            <div v-else-if="rejectedDocType === 'goodsReceipt'" class="item-row item-row-4 item-header-row">
              <span>{{ $t('employee.item_name') }}</span>
              <span>{{ $t('employee.received_qty') }}</span>
              <span>{{ $t('employee.accepted_qty') }}</span>
              <span>{{ $t('employee.line_amount') }}</span>
            </div>
            <div v-for="(item, index) in rejectedDraft.items" :key="index">
              
              <!-- Invoice Item Row -->
              <div v-if="rejectedDocType === 'invoice'" class="item-row">
                <input type="text" v-model="item.itemName" :placeholder="$t('employee.item_name')" required />
                <input type="number" min="0" v-model.number="item.quantity" :placeholder="$t('employee.quantity')" required />
                <input type="number" min="0" v-model.number="item.unitPrice" :placeholder="$t('employee.unit_price')" required />
              </div>

              <!-- Purchase Order Item Row -->
              <div v-else-if="rejectedDocType === 'purchaseOrder'" class="item-row item-row-5">
                <input type="text" v-model="item.itemName" :placeholder="$t('employee.item_name')" required />
                <input type="text" v-model="item.spec" :placeholder="$t('employee.spec')" />
                <input type="number" min="0" v-model.number="item.quantity" :placeholder="$t('employee.quantity')" required />
                <input type="number" min="0" v-model.number="item.unitPrice" :placeholder="$t('employee.unit_price')" required />
                <input type="number" min="0" v-model.number="item.lineAmount" :placeholder="$t('employee.line_amount')" required />
              </div>

              <!-- Goods Receipt Item Row -->
              <div v-else-if="rejectedDocType === 'goodsReceipt'" class="item-row item-row-4">
                <input type="text" v-model="item.itemName" :placeholder="$t('employee.item_name')" required />
                <input type="number" min="0" v-model.number="item.receivedQty" :placeholder="$t('employee.received_qty')" required />
                <input type="number" min="0" v-model.number="item.acceptedQty" :placeholder="$t('employee.accepted_qty')" required />
                <input type="number" min="0" v-model.number="item.lineAmount" :placeholder="$t('employee.line_amount')" required />
              </div>

              <div class="item-row-actions" v-if="rejectedDraft.items.length > 1">
                <button type="button" class="btn-ghost btn-small" @click="removeRejectedItem(index)">
                  {{ $t('employee.remove_item') }}
                </button>
              </div>
            </div>
            <div class="item-add">
              <button type="button" class="btn-ghost btn-small" @click="addRejectedItem">
                {{ $t('employee.add_item') }}
              </button>
            </div>
          </div>
          <p v-if="rejectedError" class="error-text">{{ rejectedError }}</p>
          <p v-if="rejectedSubmitMessage" class="success-text">{{ rejectedSubmitMessage }}</p>
          <div class="form-actions full-width">
            <button type="button" class="btn-ghost" @click="closeRejectedModal">
              {{ $t('employee.cancel') }}
            </button>
            <button type="submit" class="btn-primary" :disabled="rejectedSubmitting">
              {{ rejectedSubmitting ? $t('employee.submitting') : $t('employee.resubmit') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import { apiFetch } from '@/api.js';

const OCR_ENDPOINTS = {
  invoice: '/employee/invoices/ocr',
  purchaseOrder: '/employee/purchase-orders/ocr',
  goodsReceipt: '/employee/goods-receipts/ocr',
};

const OCR_FILE_FIELDS = {
  invoice: 'invoiceFile',
  purchaseOrder: 'poFile',
  goodsReceipt: 'grFile',
};

const OCR_POLL_INTERVAL_MS = 1500;
const OCR_POLL_TIMEOUT_MS = 180000;

const SUBMIT_ENDPOINTS = {
  invoice: '/employee/invoices',
  purchaseOrder: '/employee/purchase-orders',
  goodsReceipt: '/employee/goods-receipts',
};

const SUBMIT_FILE_FIELDS = {
  invoice: 'invoiceFile',
  purchaseOrder: 'poFile',
  goodsReceipt: 'grFile',
};

const SUBMIT_DATA_FIELDS = {
  invoice: 'invoiceData',
  purchaseOrder: 'poData',
  goodsReceipt: 'grData',
};

const DOC_TYPE_LABELS = {
  invoice: 'employee.doc_type_invoice',
  purchaseOrder: 'employee.doc_type_purchase_order',
  goodsReceipt: 'employee.doc_type_goods_receipt',
};

function emptyInvoiceItem() {
  return { lineNo: 1, itemName: '', quantity: 0, unitPrice: 0 };
}

function emptyPoItem() {
  return { lineNo: 1, itemName: '', spec: '', quantity: 0, unitPrice: 0, lineAmount: 0 };
}

function emptyGrItem() {
  return { lineNo: 1, itemName: '', receivedQty: 0, acceptedQty: 0, lineAmount: 0 };
}

function emptyInvoiceDraft() {
  return { invoiceNo: '', poNo: '', invoiceDate: '', vendorName: '', taxId: '', totalAmount: 0, items: [emptyInvoiceItem()] };
}

function emptyPoDraft() {
  return { poNo: '', purchaser: '', department: '', vendorName: '', taxId: '', poDate: '', totalAmount: 0, items: [emptyPoItem()] };
}

function emptyGrDraft() {
  return { grNo: '', poNo: '', applicant: '', receiver: '', grDate: '', totalQty: 0, totalAmount: 0, items: [emptyGrItem()] };
}

function ensureItems(items, createItem) {
  if (!Array.isArray(items) || items.length === 0) {
    return [createItem()];
  }
  return items;
}

export default {
  data() {
    return {
      activeTab: 'ocr',
      docType: 'invoice',
      uploadFile: null,
      uploadFileUrl: '',
      invoiceDraft: emptyInvoiceDraft(),
      poDraft: emptyPoDraft(),
      grDraft: emptyGrDraft(),
      hasOcrDraft: false,
      ocrLoading: false,
      ocrJob: null,
      ocrSubmitting: false,
      ocrJobs: [],
      submitLoading: false,
      apiError: '',
      submitMessage: '',
      approvedPos: [],
      poSearch: '',
      poLoading: false,
      poError: '',
      poWarning: '',
      poDropdownOpen: false,
      grPoDropdownOpen: false,
      rejectedRecords: [],
      rejectedLoading: false,
      rejectedError: '',
      rejectedModalOpen: false,
      rejectedDocType: 'invoice',
      rejectedDocId: '',
      rejectedDraft: emptyInvoiceDraft(),
      rejectedFile: null,
      rejectedFileUrl: '',
      rejectedServerFileUrl: '',
      rejectedServerFileType: '',
      rejectedServerFileLoading: false,
      rejectedOcrSubmitting: false,
      rejectedSubmitting: false,
      rejectedSubmitMessage: '',
      rejectedPoSearch: '',
      rejectedPoWarning: '',
      rejectedPoDropdownOpen: false,
      submittedRecords: [],
      submittedLoading: false,
      submittedError: '',
      selectedDocDetail: null,
      detailLoading: false,
      detailError: '',
      detailFileUrl: '',
      detailFileType: '',
      detailFileLoading: false,
      voidLoading: false,
      isDragging: false,
    };
  },
  computed: {
    filePreviewUrl() {
      if (!this.uploadFile) return '';
      return this.uploadFileUrl;
    },
    filteredApprovedPos() {
      const keyword = this.poSearch.trim().toLowerCase();
      if (!keyword) return this.approvedPos;
      return this.approvedPos.filter(po => {
        return [po.poNo, po.vendorName].some(value => String(value || '').toLowerCase().includes(keyword));
      });
    },
    filteredRejectedPos() {
      const keyword = this.rejectedPoSearch.trim().toLowerCase();
      if (!keyword) return this.approvedPos;
      return this.approvedPos.filter(po => {
        return [po.poNo, po.vendorName].some(value => String(value || '').toLowerCase().includes(keyword));
      });
    },
    rejectedPreviewUrl() {
      return this.rejectedFileUrl || this.rejectedServerFileUrl || '';
    },
    rejectedPreviewIsPdf() {
      return this.isPdfUrl(this.rejectedPreviewUrl) || this.isPdfFile(this.rejectedFile) || this.isPdfMime(this.rejectedServerFileType);
    },
    rejectedPreviewIsImage() {
      return this.isImageUrl(this.rejectedPreviewUrl) || this.isImageFile(this.rejectedFile) || this.isImageMime(this.rejectedServerFileType);
    },
    activeOcrJobCount() {
      return this.ocrJobs.filter(job => ['queued', 'processing'].includes(job.status)).length;
    },
    completedOcrJobCount() {
      return this.ocrJobs.filter(job => job.status === 'completed').length;
    },
  },
  watch: {
    docType() {
      if (this._applyingOcrJob) return;
      this.resetDrafts();
      if (this.needsApprovedPo()) {
        this.loadApprovedPos();
      }
    },
    'invoiceDraft.poNo'(value) {
      if (this.isApprovedPo(value)) {
        this.poWarning = '';
      }
    },
    'grDraft.poNo'(value) {
      if (this.isApprovedPo(value)) {
        this.poWarning = '';
      }
    },
    'rejectedDraft.poNo'(value) {
      if (this.isApprovedPo(value)) {
        this.rejectedPoWarning = '';
      }
    },
    uploadFile: {
      handler(newFile) {
        if (this.uploadFileUrl) {
          URL.revokeObjectURL(this.uploadFileUrl);
        }
        this.uploadFileUrl = newFile ? URL.createObjectURL(newFile) : '';
      },
      immediate: true,
    },
    rejectedFile: {
      handler(newFile) {
        if (this.rejectedFileUrl) {
          URL.revokeObjectURL(this.rejectedFileUrl);
        }
        this.rejectedFileUrl = newFile ? URL.createObjectURL(newFile) : '';
      },
      immediate: true,
    },
  },
  beforeDestroy() {
    this.stopAllOcrPolling();
    if (this.uploadFileUrl) {
      URL.revokeObjectURL(this.uploadFileUrl);
    }
    if (this.detailFileUrl) {
      URL.revokeObjectURL(this.detailFileUrl);
    }
    if (this.rejectedFileUrl) {
      URL.revokeObjectURL(this.rejectedFileUrl);
    }
    if (this.rejectedServerFileUrl) {
      URL.revokeObjectURL(this.rejectedServerFileUrl);
    }
    if (this._poClickOutside) {
      document.removeEventListener('mousedown', this._poClickOutside);
    }
  },
  mounted() {
    this.loadSubmittedRecords();
    if (this.needsApprovedPo()) {
      this.loadApprovedPos();
    }
    this._poClickOutside = (e) => {
      if (this.$refs.poDropdown && !this.$refs.poDropdown.contains(e.target)) {
        this.poDropdownOpen = false;
      }
      if (this.$refs.grPoDropdown && !this.$refs.grPoDropdown.contains(e.target)) {
        this.grPoDropdownOpen = false;
      }
      if (this.$refs.rejectedPoDropdown && !this.$refs.rejectedPoDropdown.contains(e.target)) {
        this.rejectedPoDropdownOpen = false;
      }
    };
    document.addEventListener('mousedown', this._poClickOutside);
  },
  beforeUnmount() {
    this.stopAllOcrPolling();
    document.removeEventListener('mousedown', this._poClickOutside);
  },
  methods: {
    isImageFile(file) {
      return file && file.type.startsWith('image/');
    },
    isPdfFile(file) {
      return file && file.type === 'application/pdf';
    },
    isImageMime(type) {
      return type && type.startsWith('image/');
    },
    isPdfMime(type) {
      return type === 'application/pdf';
    },
    isImageUrl(url) {
      return Boolean(url) && /\.(png|jpg|jpeg|gif|webp|svg)$/i.test(url);
    },
    isPdfUrl(url) {
      return Boolean(url) && /\.pdf$/i.test(url);
    },
    needsApprovedPo() {
      return this.docType === 'invoice' || this.docType === 'goodsReceipt';
    },
    docTypeLabelKey(type) {
      return DOC_TYPE_LABELS[type] || 'employee.doc_type';
    },
    resetDrafts(keepMessage = false) {
      this.hasOcrDraft = false;
      this.apiError = '';
      this.ocrJob = null;
      if (!keepMessage) {
        this.submitMessage = '';
      }
      this.invoiceDraft = emptyInvoiceDraft();
      this.poDraft = emptyPoDraft();
      this.grDraft = emptyGrDraft();
      this.poWarning = '';
      this.poSearch = '';
      this.poDropdownOpen = false;
      this.grPoDropdownOpen = false;
      this.uploadFile = null;
    },
    togglePoDropdown() {
      this.poDropdownOpen = !this.poDropdownOpen;
      this.grPoDropdownOpen = false;
      if (this.poDropdownOpen) {
        this.poSearch = '';
        this.$nextTick(() => this.$refs.poSearchInput && this.$refs.poSearchInput.focus());
      }
    },
    toggleGrPoDropdown() {
      this.grPoDropdownOpen = !this.grPoDropdownOpen;
      this.poDropdownOpen = false;
      if (this.grPoDropdownOpen) {
        this.poSearch = '';
        this.$nextTick(() => this.$refs.grPoSearchInput && this.$refs.grPoSearchInput.focus());
      }
    },
    toggleRejectedPoDropdown() {
      this.rejectedPoDropdownOpen = !this.rejectedPoDropdownOpen;
      if (this.rejectedPoDropdownOpen) {
        this.rejectedPoSearch = '';
        this.$nextTick(() => this.$refs.rejectedPoSearchInput && this.$refs.rejectedPoSearchInput.focus());
      }
    },
    selectPo(po, context) {
      if (context === 'invoice') {
        this.invoiceDraft.poNo = po.poNo;
        this.invoiceDraft.vendorName = this.invoiceDraft.vendorName || po.vendorName;
        this.poDropdownOpen = false;
        this.poSearch = '';
        this.poWarning = '';
      } else if (context === 'gr') {
        this.grDraft.poNo = po.poNo;
        this.grPoDropdownOpen = false;
        this.poSearch = '';
        this.poWarning = '';
      } else if (context === 'rejected') {
        this.rejectedDraft.poNo = po.poNo;
        this.rejectedPoDropdownOpen = false;
        this.rejectedPoSearch = '';
        this.rejectedPoWarning = '';
      }
    },
    handleNewApplication() {
      this.activeTab = 'ocr';
      this.apiError = '';
      this.submitMessage = '';
    },
    handleViewRecords(status) {
      if (status === 'rejected') {
        this.activeTab = 'rejected';
        this.loadRejectedDocuments();
      } else if (status === 'submitted') {
        this.activeTab = 'submitted';
        this.loadSubmittedRecords();
      }
    },
    handleFileUpload(event) {
      this.uploadFile = event.target.files?.[0] || null;
      this.submitMessage = '';
      console.log('[handleFileUpload] file:', this.uploadFile);
    },
    handleDrop(event) {
      this.isDragging = false;
      const file = event.dataTransfer.files?.[0];
      if (file) {
        this.uploadFile = file;
        this.submitMessage = '';
      }
    },

    async loadApprovedPos(force = false) {
      if (this.poLoading) return;
      if (this.approvedPos.length > 0 && !force) return;
      this.poLoading = true;
      this.poError = '';
      try {
        const response = await apiFetch('/employee/purchase-orders/approved');
        if (!response.ok) throw new Error(this.$t('employee.load_po_failed'));
        this.approvedPos = await response.json();
      } catch (error) {
        this.poError = error.message || this.$t('employee.load_po_failed');
      } finally {
        this.poLoading = false;
      }
    },
    isApprovedPo(poNo) {
      return this.approvedPos.some(po => po.poNo === poNo);
    },
    resolveOcrPoNo(poNo) {
      if (!this.needsApprovedPo()) return poNo || '';
      if (!poNo) return '';
      if (this.isApprovedPo(poNo)) {
        this.poWarning = '';
        return poNo;
      }
      this.poWarning = this.$t('employee.invalid_po_no');
      return '';
    },

    // ---- OCR ----
    async handleRunOcr() {
      if (!this.uploadFile) {
        this.apiError = this.$t('employee.select_doc_file');
        return;
      }
      this.ocrSubmitting = true;
      this.apiError = '';
      this.submitMessage = '';
      this.poWarning = '';
      this.ocrJob = null;

      try {
        if (this.needsApprovedPo()) {
          await this.loadApprovedPos();
        }
        const formData = new FormData();
        formData.append(OCR_FILE_FIELDS[this.docType], this.uploadFile);

        const url = `${OCR_ENDPOINTS[this.docType]}?async=true`;
        const response = await apiFetch(url, { method: 'POST', body: formData });
        if (!response.ok) throw new Error(await this.readApiError(response, this.$t('employee.ocr_failed')));
        const payload = await response.json();
        if (payload.jobId) {
          const queuedJob = this.addOcrJob(payload, this.uploadFile, this.docType);
          this.startOcrPolling(queuedJob);
          this.uploadFile = null;
          if (this.$refs.fileInput) {
            this.$refs.fileInput.value = '';
          }
        } else {
          this.fillDraft(payload);
          this.hasOcrDraft = true;
        }
      } catch (error) {
        this.apiError = error.message || this.$t('employee.ocr_failed');
      } finally {
        this.ocrSubmitting = false;
      }
    },

    sleep(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
    },

    async readApiError(response, fallback) {
      try {
        const body = await response.json();
        return body.detail || body.message || fallback;
      } catch (error) {
        return fallback;
      }
    },

    addOcrJob(payload, file, documentType) {
      const queuedJob = {
        localId: `${payload.jobId}-${Date.now()}`,
        jobId: payload.jobId,
        documentType,
        filename: file?.name || payload.filename || payload.jobId,
        file,
        status: payload.status || 'queued',
        result: null,
        error: '',
        createdAt: payload.createdAt || new Date().toISOString(),
        updatedAt: payload.updatedAt || new Date().toISOString(),
        startedAtMs: Date.now(),
        pollTimer: null,
      };
      this.ocrJobs.unshift(queuedJob);
      this.ocrJob = queuedJob;
      return queuedJob;
    },

    updateOcrJob(localId, patch) {
      const index = this.ocrJobs.findIndex(job => job.localId === localId);
      if (index === -1) return null;
      this.ocrJobs.splice(index, 1, { ...this.ocrJobs[index], ...patch });
      if (this.ocrJob?.localId === localId) {
        this.ocrJob = this.ocrJobs[index];
      }
      return this.ocrJobs[index];
    },

    startOcrPolling(job) {
      const poll = async () => {
        if (Date.now() - job.startedAtMs > OCR_POLL_TIMEOUT_MS) {
          this.updateOcrJob(job.localId, {
            status: 'failed',
            error: this.$t('employee.ocr_timeout'),
            pollTimer: null,
          });
          return;
        }

        try {
          const response = await apiFetch(`/employee/ocr-jobs/${job.jobId}`);
          if (!response.ok) {
            throw new Error(await this.readApiError(response, this.$t('employee.ocr_failed')));
          }

          const latest = await response.json();
          const updatedJob = this.updateOcrJob(job.localId, {
            status: latest.status,
            result: latest.result || null,
            error: latest.error || '',
            updatedAt: latest.updatedAt || new Date().toISOString(),
          });

          if (latest.status === 'completed' || latest.status === 'failed') {
            this.updateOcrJob(job.localId, { pollTimer: null });
            return;
          }

          const timer = window.setTimeout(poll, OCR_POLL_INTERVAL_MS);
          this.updateOcrJob(job.localId, { pollTimer: timer });
          if (updatedJob) updatedJob.pollTimer = timer;
        } catch (error) {
          this.updateOcrJob(job.localId, {
            status: 'failed',
            error: error.message || this.$t('employee.ocr_failed'),
            pollTimer: null,
          });
        }
      };

      const timer = window.setTimeout(poll, OCR_POLL_INTERVAL_MS);
      this.updateOcrJob(job.localId, { pollTimer: timer });
    },

    stopAllOcrPolling() {
      this.ocrJobs.forEach(job => {
        if (job.pollTimer) {
          window.clearTimeout(job.pollTimer);
        }
      });
    },

    async applyOcrJob(job) {
      this._applyingOcrJob = true;
      this.docType = job.documentType;
      this.uploadFile = job.file || null;
      this.apiError = '';
      this.submitMessage = '';
      this.poWarning = '';
      if (this.needsApprovedPo()) {
        await this.loadApprovedPos();
      }
      this.fillDraft(job.result || {});
      this.hasOcrDraft = true;
      this.ocrJob = job;
      this.$nextTick(() => {
        this._applyingOcrJob = false;
      });
    },

    retryOcrJob(job) {
      this.docType = job.documentType;
      this.uploadFile = job.file || null;
      this.apiError = job.error || '';
    },

    fillDraft(payload) {
      switch (this.docType) {
        case 'invoice':
          this.invoiceDraft = {
            invoiceNo: payload.invoiceNo || '',
            poNo: this.resolveOcrPoNo(payload.poNo),
            invoiceDate: payload.invoiceDate || '',
            vendorName: payload.vendorName || '',
            taxId: payload.taxId || '',
            totalAmount: payload.totalAmount || 0,
            items: ensureItems((payload.items || []).map(i => ({
              itemName: i.itemName || '',
              quantity: i.quantity || 0,
              unitPrice: i.unitPrice || 0,
            })), emptyInvoiceItem),
          };
          break;
        case 'purchaseOrder':
          this.poDraft = {
            poNo: payload.poNo || '',
            purchaser: payload.purchaser || '',
            department: payload.department || '',
            vendorName: payload.vendorName || '',
            taxId: payload.taxId || '',
            poDate: payload.poDate || '',
            totalAmount: payload.totalAmount || 0,
            items: ensureItems((payload.items || []).map(i => ({
              itemName: i.itemName || '',
              spec: i.spec || '',
              quantity: i.quantity || 0,
              unitPrice: i.unitPrice || 0,
              lineAmount: i.lineAmount || 0,
            })), emptyPoItem),
          };
          break;
        case 'goodsReceipt':
          this.grDraft = {
            grNo: payload.grNo || '',
            poNo: this.resolveOcrPoNo(payload.poNo),
            applicant: payload.applicant || '',
            receiver: payload.receiver || '',
            grDate: payload.grDate || '',
            totalQty: payload.totalQty || 0,
            totalAmount: payload.totalAmount || 0,
            items: ensureItems((payload.items || []).map(i => ({
              itemName: i.itemName || '',
              receivedQty: i.receivedQty || 0,
              acceptedQty: i.acceptedQty || 0,
              lineAmount: i.lineAmount || 0,
            })), emptyGrItem),
          };
          break;
      }
    },

    validatePoSelection(poNo) {
      if (!this.needsApprovedPo()) return true;
      if (!poNo) {
        this.apiError = this.$t('employee.po_no_required');
        return false;
      }
      if (!this.isApprovedPo(poNo)) {
        this.apiError = this.$t('employee.invalid_po_no');
        return false;
      }
      return true;
    },

    // ---- Submit ----
    async handleSubmit() {
      if (!this.hasOcrDraft) {
        this.apiError = this.$t('employee.complete_ocr_first');
        return;
      }
      if (!this.uploadFile) {
        this.apiError = this.$t('employee.select_doc_file');
        return;
      }
      this.submitLoading = true;
      this.apiError = '';
      try {
        const formData = new FormData();
        const draftMap = {
          invoice: this.invoiceDraft,
          purchaseOrder: this.poDraft,
          goodsReceipt: this.grDraft,
        };
        const draft = draftMap[this.docType];

        if (!this.validatePoSelection(draft.poNo)) {
          this.submitLoading = false;
          return;
        }

        const items = (draft.items || []).map((item, index) => ({
          lineNo: index + 1,
          ...item,
        }));

        formData.append(SUBMIT_FILE_FIELDS[this.docType], this.uploadFile);
        formData.append(SUBMIT_DATA_FIELDS[this.docType], JSON.stringify({
          ...draft,
          items,
        }));

        const url = SUBMIT_ENDPOINTS[this.docType];
        const response = await apiFetch(url, { method: 'POST', body: formData });
        if (!response.ok) {
          let detail = '';
          try {
            const errBody = await response.json();
            if (Array.isArray(errBody.detail)) {
              detail = errBody.detail.map(d => d.msg || JSON.stringify(d)).join('; ');
            } else {
              detail = errBody.detail || errBody.message || JSON.stringify(errBody);
            }
          } catch (e) {
            detail = `HTTP ${response.status}`;
          }
          throw new Error(detail || this.$t('employee.submit_failed'));
        }
        const successKeyMap = {
          invoice: 'employee.submit_success_invoice',
          purchaseOrder: 'employee.submit_success_purchase_order',
          goodsReceipt: 'employee.submit_success_goods_receipt',
        };
        this.submitMessage = successKeyMap[this.docType] || 'employee.submit_success';
        this.resetDrafts(true);
        await this.loadSubmittedRecords();
      } catch (error) {
        this.apiError = error.message || this.$t('employee.submit_failed');
      } finally {
        this.submitLoading = false;
      }
    },

    addInvoiceItem() {
      this.invoiceDraft.items.push(emptyInvoiceItem());
    },
    removeInvoiceItem(index) {
      this.invoiceDraft.items.splice(index, 1);
      this.invoiceDraft.items = ensureItems(this.invoiceDraft.items, emptyInvoiceItem);
    },
    addPoItem() {
      this.poDraft.items.push(emptyPoItem());
    },
    removePoItem(index) {
      this.poDraft.items.splice(index, 1);
      this.poDraft.items = ensureItems(this.poDraft.items, emptyPoItem);
    },
    addGrItem() {
      this.grDraft.items.push(emptyGrItem());
    },
    removeGrItem(index) {
      this.grDraft.items.splice(index, 1);
      this.grDraft.items = ensureItems(this.grDraft.items, emptyGrItem);
    },
    addRejectedItem() {
      if (this.rejectedDocType === 'invoice') {
        this.rejectedDraft.items.push(emptyInvoiceItem());
      } else if (this.rejectedDocType === 'purchaseOrder') {
        this.rejectedDraft.items.push(emptyPoItem());
      } else if (this.rejectedDocType === 'goodsReceipt') {
        this.rejectedDraft.items.push(emptyGrItem());
      }
    },
    removeRejectedItem(index) {
      this.rejectedDraft.items.splice(index, 1);
      if (this.rejectedDocType === 'invoice') {
        this.rejectedDraft.items = ensureItems(this.rejectedDraft.items, emptyInvoiceItem);
      } else if (this.rejectedDocType === 'purchaseOrder') {
        this.rejectedDraft.items = ensureItems(this.rejectedDraft.items, emptyPoItem);
      } else if (this.rejectedDocType === 'goodsReceipt') {
        this.rejectedDraft.items = ensureItems(this.rejectedDraft.items, emptyGrItem);
      }
    },
    async loadSubmittedRecords() {
      this.submittedLoading = true;
      this.submittedError = '';
      try {
        const response = await apiFetch('/employee/documents');
        if (!response.ok) throw new Error(this.$t('employee.load_submitted_failed'));
        this.submittedRecords = await response.json();
      } catch (error) {
        this.submittedError = error.message || this.$t('employee.load_submitted_failed');
        this.submittedRecords = [];
      } finally {
        this.submittedLoading = false;
      }
    },
    formatStatus(status) {
      // pendingMatch, pending -> pending
      // approved, onHold -> approved
      // rejected -> rejected
      // void -> void
      const statusMap = {
        pendingMatch: 'pending',
        pending: 'pending',
        approved: 'approved',
        onHold: 'approved',
        rejected: 'rejected',
        void: 'void',
      }
      return statusMap[status] || status;
    },
    async loadDocumentDetail(docId) {
      this.detailLoading = true;
      this.detailError = '';
      this.selectedDocDetail = null;
      if (this.detailFileUrl) {
        URL.revokeObjectURL(this.detailFileUrl);
        this.detailFileUrl = '';
      }
      this.detailFileType = '';
      try {
        const response = await apiFetch(`/employee/documents/${docId}`);
        if (!response.ok) throw new Error(this.$t('employee.load_detail_failed'));
        this.selectedDocDetail = await response.json();
      } catch (error) {
        this.detailError = error.message || this.$t('employee.load_detail_failed');
      } finally {
        this.detailLoading = false;
      }
    },
    clearDocumentDetail() {
      this.selectedDocDetail = null;
      this.detailError = '';
      if (this.detailFileUrl) {
        URL.revokeObjectURL(this.detailFileUrl);
        this.detailFileUrl = '';
      }
      this.detailFileType = '';
    },
    async previewDocumentFile(docId) {
      this.detailFileLoading = true;
      this.detailError = '';
      try {
        const response = await apiFetch(`/employee/documents/${docId}/file`);
        if (!response.ok) throw new Error(this.$t('employee.load_file_failed'));
        const contentType = response.headers.get('content-type') || '';
        const blob = await response.blob();
        if (this.detailFileUrl) {
          URL.revokeObjectURL(this.detailFileUrl);
        }
        this.detailFileType = contentType;
        this.detailFileUrl = URL.createObjectURL(blob);
      } catch (error) {
        this.detailError = error.message || this.$t('employee.load_file_failed');
      } finally {
        this.detailFileLoading = false;
      }
    },
    async loadRejectedServerFile(docId) {
      this.rejectedServerFileLoading = true;
      try {
        const response = await apiFetch(`/employee/documents/${docId}/file`);
        if (!response.ok) throw new Error(this.$t('employee.load_file_failed'));
        const contentType = response.headers.get('content-type') || '';
        const blob = await response.blob();
        this.rejectedServerFileType = contentType;
        this.rejectedServerFileUrl = URL.createObjectURL(blob);
      } catch (error) {
        this.rejectedError = error.message || this.$t('employee.load_file_failed');
      } finally {
        this.rejectedServerFileLoading = false;
      }
    },
    async loadRejectedDocuments() {
      this.rejectedLoading = true;
      this.rejectedError = '';
      try {
        const response = await apiFetch('/employee/documents/rejected');
        if (!response.ok) throw new Error(this.$t('employee.load_rejected_failed'));
        this.rejectedRecords = await response.json();
      } catch (error) {
        this.rejectedError = error.message || this.$t('employee.load_rejected_failed');
        this.rejectedRecords = [];
      } finally {
        this.rejectedLoading = false;
      }
    },
    async openRejectedModal(record) {
      this.rejectedModalOpen = true;
      this.rejectedError = '';
      this.rejectedSubmitMessage = '';
      this.rejectedPoWarning = '';
      this.rejectedPoSearch = '';
      this.rejectedServerFileUrl = '';
      this.rejectedServerFileType = '';
      this.rejectedDocType = record.docType || 'invoice';
      this.rejectedDocId = record.docId || '';

      // Set fallback empty draft first
      if (this.rejectedDocType === 'invoice') {
        this.rejectedDraft = emptyInvoiceDraft();
      } else if (this.rejectedDocType === 'purchaseOrder') {
        this.rejectedDraft = emptyPoDraft();
      } else if (this.rejectedDocType === 'goodsReceipt') {
        this.rejectedDraft = emptyGrDraft();
      }

      // Fetch the actual record details to populate the form correctly
      try {
        if (record.docId) {
          const response = await apiFetch(`/employee/documents/${record.docId}`);
          if (response.ok) {
            const detail = await response.json();
            const formData = detail.formData || {};
            const items = detail.items || [];
            if (this.rejectedDocType === 'invoice') {
               this.rejectedDraft = { ...emptyInvoiceDraft(), ...formData, items: ensureItems(items, emptyInvoiceItem) };
            } else if (this.rejectedDocType === 'purchaseOrder') {
               this.rejectedDraft = { ...emptyPoDraft(), ...formData, items: ensureItems(items, emptyPoItem) };
            } else if (this.rejectedDocType === 'goodsReceipt') {
               this.rejectedDraft = { ...emptyGrDraft(), ...formData, items: ensureItems(items, emptyGrItem) };
            }
          }
        }
      } catch (err) {
        console.warn('Failed to load document details for edit', err);
      }

      if (this.approvedPos.length > 0 && this.rejectedDraft.poNo && !this.isApprovedPo(this.rejectedDraft.poNo)) {
        this.rejectedPoWarning = this.$t('employee.invalid_po_no');
      }
      this.loadApprovedPos();
      if (record.docId) {
        this.loadRejectedServerFile(record.docId);
      }
    },
    closeRejectedModal() {
      this.rejectedModalOpen = false;
      this.rejectedDraft = emptyInvoiceDraft();
      this.rejectedFile = null;
      this.rejectedOcrSubmitting = false;
      if (this.rejectedServerFileUrl) {
        URL.revokeObjectURL(this.rejectedServerFileUrl);
        this.rejectedServerFileUrl = '';
      }
      this.rejectedServerFileType = '';
      this.rejectedError = '';
      this.rejectedSubmitMessage = '';
      this.rejectedPoWarning = '';
      this.rejectedPoSearch = '';
    },
    handleRejectedFileChange(event) {
      this.rejectedFile = event.target.files?.[0] || null;
    },
    applyRejectedOcr(payload) {
      const mappedItems = (payload.items || []).map(item => ({
        itemName: item.itemName || '',
        quantity: item.quantity || 0,
        unitPrice: item.unitPrice || 0,
      }));
      const nextItems = mappedItems.length > 0
        ? ensureItems(mappedItems, emptyInvoiceItem)
        : ensureItems(this.rejectedDraft.items, emptyInvoiceItem);

      this.rejectedDraft = {
        ...this.rejectedDraft,
        invoiceDate: payload.invoiceDate || this.rejectedDraft.invoiceDate,
        vendorName: payload.vendorName || this.rejectedDraft.vendorName,
        taxId: payload.taxId || this.rejectedDraft.taxId,
        totalAmount: payload.totalAmount || this.rejectedDraft.totalAmount,
        items: nextItems,
      };
    },
    async handleRejectedOcr() {
      if (!this.rejectedFile) {
        this.rejectedError = this.$t('employee.select_doc_file');
        return;
      }
      this.rejectedOcrSubmitting = true;
      this.rejectedError = '';
      try {
        const formData = new FormData();
        const ocrEndpoint = {
          invoice: '/employee/invoices/ocr',
          purchaseOrder: '/employee/purchase-orders/ocr',
          goodsReceipt: '/employee/goods-receipts/ocr'
        }[this.rejectedDocType] || '/employee/invoices/ocr';
        
        const fileField = {
          invoice: 'invoiceFile',
          purchaseOrder: 'poFile',
          goodsReceipt: 'grFile'
        }[this.rejectedDocType] || 'invoiceFile';

        formData.append(fileField, this.rejectedFile);
        const response = await apiFetch(ocrEndpoint, { method: 'POST', body: formData });
        if (!response.ok) {
          throw new Error(await this.readApiError(response, this.$t('employee.ocr_failed')));
        }
        const payload = await response.json();
        
        // Map payload back to rejected draft depending on type
        if (this.rejectedDocType === 'invoice') {
          const mappedItems = (payload.items || []).map(item => ({ itemName: item.itemName || '', quantity: item.quantity || 0, unitPrice: item.unitPrice || 0 }));
          const nextItems = mappedItems.length > 0 ? ensureItems(mappedItems, emptyInvoiceItem) : ensureItems(this.rejectedDraft.items, emptyInvoiceItem);
          this.rejectedDraft = { ...this.rejectedDraft, invoiceDate: payload.invoiceDate || this.rejectedDraft.invoiceDate, vendorName: payload.vendorName || this.rejectedDraft.vendorName, taxId: payload.taxId || this.rejectedDraft.taxId, totalAmount: payload.totalAmount || this.rejectedDraft.totalAmount, items: nextItems };
        } else if (this.rejectedDocType === 'purchaseOrder') {
          const mappedItems = (payload.items || []).map(item => ({ itemName: item.itemName || '', spec: item.spec || '', quantity: item.quantity || 0, unitPrice: item.unitPrice || 0, lineAmount: item.lineAmount || 0 }));
          const nextItems = mappedItems.length > 0 ? ensureItems(mappedItems, emptyPoItem) : ensureItems(this.rejectedDraft.items, emptyPoItem);
          this.rejectedDraft = { ...this.rejectedDraft, purchaser: payload.purchaser || this.rejectedDraft.purchaser, department: payload.department || this.rejectedDraft.department, vendorName: payload.vendorName || this.rejectedDraft.vendorName, poDate: payload.poDate || this.rejectedDraft.poDate, totalAmount: payload.totalAmount || this.rejectedDraft.totalAmount, items: nextItems };
        } else if (this.rejectedDocType === 'goodsReceipt') {
          const mappedItems = (payload.items || []).map(item => ({ itemName: item.itemName || '', receivedQty: item.receivedQty || 0, acceptedQty: item.acceptedQty || 0, lineAmount: item.lineAmount || 0 }));
          const nextItems = mappedItems.length > 0 ? ensureItems(mappedItems, emptyGrItem) : ensureItems(this.rejectedDraft.items, emptyGrItem);
          this.rejectedDraft = { ...this.rejectedDraft, applicant: payload.applicant || this.rejectedDraft.applicant, receiver: payload.receiver || this.rejectedDraft.receiver, grDate: payload.grDate || this.rejectedDraft.grDate, totalQty: payload.totalQty || this.rejectedDraft.totalQty, totalAmount: payload.totalAmount || this.rejectedDraft.totalAmount, items: nextItems };
        }
      } catch (error) {
        this.rejectedError = error.message || this.$t('employee.ocr_failed');
      } finally {
        this.rejectedOcrSubmitting = false;
      }
    },
    async handleRejectedResubmit() {
      this.rejectedSubmitting = true;
      this.rejectedError = '';
      this.rejectedSubmitMessage = '';
      try {
        if (['invoice', 'goodsReceipt'].includes(this.rejectedDocType)) {
          if (this.approvedPos.length === 0) {
            await this.loadApprovedPos(true);
          }
          if (!this.isApprovedPo(this.rejectedDraft.poNo)) {
            this.rejectedError = this.$t('employee.invalid_po_no');
            this.rejectedSubmitting = false;
            return;
          }
        }
        const formData = new FormData();
        if (this.rejectedFile) {
          formData.append('docFile', this.rejectedFile);
        }
        const items = (this.rejectedDraft.items || []).map((item, index) => ({
          lineNo: index + 1,
          ...item,
        }));

        // Build clean payload with only DB-expected keys per doc type
        let cleanDocData = {};
        if (this.rejectedDocType === 'invoice') {
          const invoiceKeys = ['invoiceNo', 'invoiceDate', 'totalAmount', 'taxRate', 'poNo', 'note'];
          for (const key of invoiceKeys) {
            if (this.rejectedDraft[key] !== undefined && this.rejectedDraft[key] !== null) {
              cleanDocData[key] = this.rejectedDraft[key];
            }
          }
        } else if (this.rejectedDocType === 'purchaseOrder') {
          const poKeys = ['poNo', 'totalAmount', 'vendorName', 'note'];
          for (const key of poKeys) {
            if (this.rejectedDraft[key] !== undefined && this.rejectedDraft[key] !== null) {
              cleanDocData[key] = this.rejectedDraft[key];
            }
          }
          // Remap: poDate → orderDate, taxId → vendorTaxId
          if (this.rejectedDraft.poDate) cleanDocData.orderDate = this.rejectedDraft.poDate;
          if (this.rejectedDraft.taxId) cleanDocData.vendorTaxId = this.rejectedDraft.taxId;
        } else if (this.rejectedDocType === 'goodsReceipt') {
          const grKeys = ['grNo', 'poNo', 'note'];
          for (const key of grKeys) {
            if (this.rejectedDraft[key] !== undefined && this.rejectedDraft[key] !== null) {
              cleanDocData[key] = this.rejectedDraft[key];
            }
          }
          // Remap: grDate → receivedDate
          if (this.rejectedDraft.grDate) cleanDocData.receivedDate = this.rejectedDraft.grDate;
        }

        formData.append('docData', JSON.stringify({
          ...cleanDocData,
          items,
        }));

        const response = await apiFetch(`/employee/documents/${this.rejectedDocId}`, {
          method: 'PUT',
          body: formData,
        });
        if (!response.ok) {
          let detail = '';
          try {
            const errBody = await response.json();
            detail = errBody.detail || errBody.message || JSON.stringify(errBody);
          } catch (e) {
            detail = `HTTP ${response.status}`;
          }
          console.error('[handleRejectedResubmit] Resubmit failed:', detail);
          throw new Error(detail || this.$t('employee.resubmit_failed'));
        }
        
        this.rejectedSubmitMessage = this.$t('employee.resubmit_success');
        await this.loadRejectedDocuments();
        await this.loadSubmittedRecords();
      } catch (error) {
        console.error('[handleRejectedResubmit] Error:', error);
        this.rejectedError = error.message || this.$t('employee.resubmit_failed');
      } finally {
        this.rejectedSubmitting = false;
      }
    },
    async handleVoidDocument(docId) {
      if (!confirm(this.$t('employee.void_confirm'))) return;
      this.voidLoading = true;
      this.detailError = '';
      try {
        const response = await apiFetch(`/employee/documents/${docId}`, {
          method: 'DELETE',
        });
        if (!response.ok) {
          let detail = '';
          try {
            const errBody = await response.json();
            detail = errBody.detail || errBody.message || JSON.stringify(errBody);
          } catch (e) {
            detail = `HTTP ${response.status}`;
          }
          throw new Error(detail || this.$t('employee.void_failed'));
        }
        this.clearDocumentDetail();
        await this.loadSubmittedRecords();
      } catch (error) {
        this.detailError = error.message || this.$t('employee.void_failed');
      } finally {
        this.voidLoading = false;
      }
    },
  },
};
</script>

<style scoped>
/* ====== 基礎設定 ====== */
.system-container {
  background: linear-gradient(135deg, #f0fdf4 0%, #f8fafc 50%, #eff6ff 100%);
  min-height: 100vh;
  padding: 2rem 1rem 4rem;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.system-block {
  max-width: 960px;
  margin: 0 auto;
}

/* ====== 導覽列 ====== */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 0.75rem;
  background: #ffffff;
  padding: 0.5rem;
  border-radius: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.status-group {
  display: flex;
  flex-wrap: wrap;
  background: #f1f5f9;
  padding: 0.3rem;
  border-radius: 10px;
  gap: 0.2rem;
}

.nav-btn {
  border: none;
  background: transparent;
  padding: 0.65rem 1.2rem;
  border-radius: 10px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all 0.25s ease;
  white-space: nowrap;
  font-size: 0.9rem;
}

.nav-btn:hover {
  color: #10b981;
  background: rgba(16, 185, 129, 0.06);
}

.nav-btn.active {
  background: #10b981;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

/* ====== 卡片容器 ====== */
.section-card {
  background: #ffffff;
  border-radius: 20px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.06);
  padding: 2.5rem clamp(1.2rem, 4vw, 2.5rem);
  border: 1px solid #e2e8f0;
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}

.section-title {
  margin-bottom: 2rem;
  color: #1e293b;
  font-size: 1.4rem;
  font-weight: 700;
  text-align: left;
  border-left: 4px solid #10b981;
  padding-left: 1rem;
}

/* ====== Step 區塊 ====== */
.step-box {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 1.8rem;
  margin-bottom: 1.5rem;
  background: linear-gradient(to bottom, #ffffff, #f8fafc);
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
}

.step-title {
  margin: 0;
  color: #0f172a;
  font-size: 1.05rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.file-hint {
  margin-top: 0.75rem;
  color: #64748b;
  font-size: 0.88rem;
}

/* ====== 表單 ====== */
.application-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.2rem;
}

.full-width {
  grid-column: 1 / -1;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  text-align: left;
}

.file-input-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
  letter-spacing: 0.02em;
}

input:not([type="file"]) {
  padding: 0.75rem 0.9rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  outline: none;
  transition: all 0.2s ease;
  font-size: 0.95rem;
  background: #ffffff;
}

input:not([type="file"]):hover {
  border-color: #cbd5e1;
}

input:focus {
  border-color: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.12);
}

.file-input-hidden {
  display: none;
}

.file-drop-zone {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 140px;
  border: 2px dashed #cbd5e1;
  border-radius: 14px;
  background: linear-gradient(135deg, #f0fdf4 0%, #f8fafc 100%);
  cursor: pointer;
  transition: all 0.25s ease;
}

.file-drop-zone:hover {
  border-color: #10b981;
  background: linear-gradient(135deg, #e6f9ee 0%, #f0fdf4 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.10);
}

.file-drop-zone--active {
  border-color: #10b981;
  background: linear-gradient(135deg, #d1fae5 0%, #e6f9ee 100%);
  box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.12);
}

.file-drop-zone--has-file {
  border-style: solid;
  border-color: #10b981;
}

.file-drop-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 1rem;
  text-align: center;
}

.file-drop-icon {
  width: 40px;
  height: 40px;
  color: #94a3b8;
  transition: color 0.2s;
}

.file-drop-zone:hover .file-drop-icon {
  color: #10b981;
}

.file-drop-icon--ok {
  color: #10b981;
}

.file-drop-text {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 500;
  color: #475569;
  word-break: break-all;
}

.file-drop-done .file-drop-text {
  color: #10b981;
  font-weight: 600;
}

.file-drop-hint {
  font-size: 0.78rem;
  color: #94a3b8;
}

.amount-input {
  position: relative;
  display: flex;
  align-items: center;
}

.currency {
  position: absolute;
  left: 1rem;
  color: #94a3b8;
  font-weight: 600;
}

.amount-input input {
  padding-left: 2rem !important;
  width: 100%;
}

.form-actions {
  grid-column: span 2;
  margin-top: 1.2rem;
  display: flex;
  gap: 1rem;
}

/* ====== 按鈕 ====== */
.btn-primary {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
  border: none;
  padding: 0.8rem 2rem;
  border-radius: 10px;
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
}

.btn-primary:disabled {
  cursor: not-allowed;
  opacity: 0.5;
  transform: none;
  box-shadow: none;
}

.btn-ghost {
  background: transparent;
  color: #64748b;
  border: 1.5px solid #e2e8f0;
  padding: 0.8rem 2rem;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-ghost:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.btn-danger {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  border: none;
  padding: 0.8rem 2rem;
  border-radius: 10px;
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 4px 14px rgba(239, 68, 68, 0.3);
}

.btn-danger:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(239, 68, 68, 0.4);
}

.btn-danger:disabled {
  cursor: not-allowed;
  opacity: 0.5;
  transform: none;
  box-shadow: none;
}

.btn-small {
  padding: 0.45rem 0.8rem;
  font-size: 0.82rem;
}

/* ====== 表格 ====== */
.table-responsive {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.modern-table {
  width: max-content;
  min-width: 100%;
  border-collapse: separate;
  border-spacing: 0 0.4rem;
}

.modern-table th {
  padding: 0.9rem 1.2rem;
  color: #94a3b8;
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  border-bottom: 2px solid #f1f5f9;
  white-space: nowrap;
}

.modern-table td {
  padding: 0.9rem 1.2rem;
  background: #ffffff;
  border-bottom: 1px solid #f1f5f9;
  white-space: nowrap;
  font-size: 0.92rem;
}

.modern-table tbody tr {
  transition: background 0.15s ease;
}

.modern-table tbody tr:hover td {
  background: #f0fdf4;
}

.text-bold {
  font-weight: 600;
  color: #1e293b;
}

/* ====== 明細 ====== */
.items-title {
  margin-bottom: 0.6rem;
  color: #1e293b;
  font-weight: 600;
}

.item-row {
  display: grid;
  grid-template-columns: 1.7fr minmax(0, 1fr) minmax(0, 1fr);
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.item-row-4 {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.item-row-5 {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.item-header-row {
  margin-bottom: 0.35rem;
  color: #475569;
  font-size: 0.85rem;
  font-weight: 600;
}

.item-header-row span {
  padding: 0 0.75rem;
}

.item-row input {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.item-row-actions {
  display: flex;
  justify-content: flex-end;
  margin: 0.3rem 0 0.6rem;
}

.item-add {
  display: flex;
  margin-top: 0.2rem;
}

.detail-panel {
  margin-top: 1.8rem;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1.5rem;
  background: #ffffff;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.04);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.detail-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
  margin-bottom: 1rem;
}

.detail-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.7rem 0.9rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.detail-label {
  font-size: 0.74rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.detail-value {
  font-size: 0.92rem;
  font-weight: 600;
  color: #1e293b;
}

.detail-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 1rem;
}

.detail-table {
  margin-top: 0.5rem;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  z-index: 1000;
}

.modal-card {
  width: min(960px, 100%);
  max-height: 90vh;
  overflow: auto;
  background: #ffffff;
  border-radius: 18px;
  padding: 1.6rem;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.25);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.2rem;
}

.modal-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: #0f172a;
}

/* ====== 單據類型選擇 ====== */
.doc-type-select {
  padding: 0.75rem 0.9rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  outline: none;
  font-size: 0.95rem;
  background: #ffffff;
  transition: all 0.2s ease;
  cursor: pointer;
}

.doc-type-select:hover {
  border-color: #cbd5e1;
}

.doc-type-select:focus {
  border-color: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.12);
}

/* ====== PO 整合搜尋下拉 ====== */
.po-dropdown {
  position: relative;
  width: 100%;
}

.po-dropdown-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 0.9rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  background: #ffffff;
  cursor: pointer;
  font-size: 0.95rem;
  color: #1e293b;
  transition: all 0.2s ease;
  user-select: none;
  min-height: 46px;
}

.po-dropdown-trigger:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.po-dropdown--open .po-dropdown-trigger {
  border-color: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.12);
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
}

.po-dropdown-value {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.po-dropdown-placeholder {
  color: #94a3b8;
}

.po-dropdown-arrow {
  color: #94a3b8;
  font-size: 0.8rem;
  margin-left: 0.5rem;
  transition: transform 0.2s ease;
}

.po-dropdown--open .po-dropdown-arrow {
  transform: rotate(180deg);
  color: #10b981;
}

.po-dropdown-panel {
  position: absolute;
  top: calc(100% - 1.5px);
  left: 0;
  right: 0;
  z-index: 200;
  background: #ffffff;
  border: 1.5px solid #10b981;
  border-top: none;
  border-bottom-left-radius: 10px;
  border-bottom-right-radius: 10px;
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  animation: poDropdownIn 0.15s ease-out;
}

@keyframes poDropdownIn {
  from { opacity: 0; transform: translateY(-6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.po-dropdown-search-wrap {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.6rem 0.7rem;
  border-bottom: 1px solid #f1f5f9;
  background: #f8fafc;
}

.po-dropdown-search {
  flex: 1;
  padding: 0.5rem 0.7rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 8px;
  outline: none;
  font-size: 0.88rem;
  background: #ffffff;
  transition: border-color 0.15s;
}

.po-dropdown-search:focus {
  border-color: #10b981;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.12);
}

.po-refresh-btn {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1.5px solid #e2e8f0;
  border-radius: 7px;
  background: #ffffff;
  color: #64748b;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.15s;
  padding: 0;
  line-height: 1;
}

.po-refresh-btn:hover:not(:disabled) {
  border-color: #10b981;
  color: #10b981;
  background: #f0fdf4;
}

.po-refresh-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.po-dropdown-list {
  list-style: none;
  margin: 0;
  padding: 0.35rem 0;
  max-height: 220px;
  overflow-y: auto;
}

.po-dropdown-list::-webkit-scrollbar {
  width: 5px;
}
.po-dropdown-list::-webkit-scrollbar-track { background: transparent; }
.po-dropdown-list::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }

.po-dropdown-item {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  padding: 0.55rem 0.9rem;
  cursor: pointer;
  transition: background 0.12s;
}

.po-dropdown-item:hover {
  background: #f0fdf4;
}

.po-dropdown-item--selected {
  background: #ecfdf5;
}

.po-dropdown-item--selected .po-item-no {
  color: #059669;
  font-weight: 700;
}

.po-item-no {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1e293b;
}

.po-item-meta {
  font-size: 0.78rem;
  color: #64748b;
}

.po-dropdown-empty {
  padding: 0.8rem 0.9rem;
  color: #94a3b8;
  font-size: 0.88rem;
  text-align: center;
  font-style: italic;
}

.helper-text {
  font-size: 0.8rem;
  margin-top: 0.35rem;
}

.ocr-job-status {
  margin: 0;
  color: #475569;
}

.ocr-queue-panel {
  border: 1px solid #dbeafe;
  border-radius: 14px;
  padding: 1rem;
  margin-bottom: 1.5rem;
  background: #f8fafc;
}

.ocr-queue-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.8rem;
}

.ocr-queue-stats {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  font-size: 0.78rem;
  color: #475569;
}

.ocr-queue-stats span {
  padding: 0.28rem 0.55rem;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
}

.ocr-job-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.ocr-queue-empty {
  padding: 1rem;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  color: #64748b;
  background: #ffffff;
  font-size: 0.88rem;
  text-align: center;
}

.ocr-job-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 0.7rem;
  padding: 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #ffffff;
}

.ocr-job-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.ocr-job-doc {
  color: #0f172a;
  font-size: 0.9rem;
  font-weight: 700;
}

.ocr-job-file {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #64748b;
  font-size: 0.78rem;
}

.ocr-job-badge {
  justify-self: end;
  min-width: 78px;
  text-align: center;
  padding: 0.3rem 0.55rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
}

.ocr-job-badge--queued {
  color: #0369a1;
  background: #e0f2fe;
}

.ocr-job-badge--processing {
  color: #7c3aed;
  background: #ede9fe;
}

.ocr-job-badge--completed {
  color: #047857;
  background: #d1fae5;
}

.ocr-job-badge--failed {
  color: #b91c1c;
  background: #fee2e2;
}

.warning-text {
  color: #b45309;
  background: #fffbeb;
  padding: 0.4rem 0.6rem;
  border-radius: 8px;
}

.file-preview-box {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 1.2rem;
  margin-bottom: 1.5rem;
  background: #ffffff;
}

/* ====== 提示訊息 ====== */
.error-text {
  color: #dc2626;
  margin-top: 0.75rem;
  padding: 0.6rem 1rem;
  background: #fef2f2;
  border-radius: 8px;
  font-size: 0.9rem;
}

.success-text {
  color: #15803d;
  margin-top: 0.75rem;
  padding: 0.6rem 1rem;
  background: #f0fdf4;
  border-radius: 8px;
  font-size: 0.9rem;
}

/* ====== 動畫 ====== */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}
.slide-fade-leave-active {
  transition: all 0.2s cubic-bezier(1, 0.5, 0.8, 1);
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(10px);
  opacity: 0;
}

/* ====== 狀態 ====== */
.empty-state {
  padding: 3rem;
  color: #94a3b8;
  font-style: italic;
  text-align: center;
}

.status-badge {
  display: inline-block;
  padding: 0.3rem 0.8rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.status-pending {
  background: #fef3c7;
  color: #d97706;
}

.status-approved {
  background: #d1fae5;
  color: #059669;
}

.status-rejected {
  background: #fee2e2;
  color: #dc2626;
}

.status-pendingMatch {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-onHold {
  background: #fef3c7;
  color: #b45309;
}

.status-void {
  background: #e2e8f0;
  color: #475569;
}

.status-pendingReview {
  background: #fde68a;
  color: #b45309;
}

/* ====== RWD ====== */
@media (max-width: 768px) {
  .system-container {
    padding: 1rem 0.5rem 3rem;
  }

  .dashboard-header {
    flex-direction: column;
    align-items: stretch;
  }

  .application-form {
    grid-template-columns: 1fr;
  }

  .form-actions {
    grid-column: 1;
  }

  .item-row,
  .item-row-4,
  .item-row-5 {
    grid-template-columns: 1fr;
  }

  .item-header-row {
    display: none;
  }

  .ocr-queue-header,
  .ocr-job-row {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .ocr-queue-header {
    flex-direction: column;
  }

  .ocr-job-badge {
    justify-self: start;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .modal-card {
    padding: 1.1rem;
  }
}
</style>
