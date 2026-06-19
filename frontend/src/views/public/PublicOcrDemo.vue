<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'

const fileInput = ref(null)
const selectedFile = ref(null)
const filePreviewUrl = ref('')
const isLoading = ref(false)
const errorMessage = ref('')
const result = ref(null)

const tokens = computed(() => Array.isArray(result.value?.tokens) ? result.value.tokens : [])
const texts = computed(() => Array.isArray(result.value?.texts) ? result.value.texts : [])
const isImagePreview = computed(() => selectedFile.value?.type?.startsWith('image/'))
const isPdfPreview = computed(() => selectedFile.value?.type === 'application/pdf')

const bounds = computed(() => {
  if (!tokens.value.length) {
    return { width: 100, height: 100 }
  }

  const maxX = Math.max(...tokens.value.map((token) => Number(token.x) || 0))
  const maxY = Math.max(...tokens.value.map((token) => Number(token.y) || 0))
  return {
    width: Math.max(maxX + 260, 480),
    height: Math.max(maxY + 80, 320)
  }
})

const previewTokens = computed(() => {
  return tokens.value.map((token, index) => {
    const x = Number(token.x) || 0
    const y = Number(token.y) || 0
    return {
      ...token,
      id: `${index}-${token.text}`,
      left: `${Math.min(Math.max((x / bounds.value.width) * 100, 0), 96)}%`,
      top: `${Math.min(Math.max((y / bounds.value.height) * 100, 0), 94)}%`
    }
  })
})

function publicOcrEndpoint() {
  const base = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '')
  return `${base}/public/ocr-demo`
}

function chooseFile() {
  fileInput.value?.click()
}

function clearFilePreviewUrl() {
  if (filePreviewUrl.value) {
    URL.revokeObjectURL(filePreviewUrl.value)
    filePreviewUrl.value = ''
  }
}

function onFileChange(event) {
  const [file] = event.target.files || []
  clearFilePreviewUrl()
  selectedFile.value = file || null
  filePreviewUrl.value = file ? URL.createObjectURL(file) : ''
  result.value = null
  errorMessage.value = ''
}

async function submitOcr() {
  if (!selectedFile.value || isLoading.value) return

  isLoading.value = true
  errorMessage.value = ''
  result.value = null

  const formData = new FormData()
  formData.append('file', selectedFile.value)

  try {
    const response = await fetch(publicOcrEndpoint(), {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      let detail = `HTTP ${response.status}`
      try {
        const errorBody = await response.json()
        detail = errorBody.detail || detail
      } catch {
        detail = await response.text()
      }
      throw new Error(detail)
    }

    result.value = await response.json()
  } catch (error) {
    errorMessage.value = error?.message || String(error)
  } finally {
    isLoading.value = false
  }
}

onBeforeUnmount(clearFilePreviewUrl)
</script>

<template>
  <main class="ocr-demo-page">
    <section class="top-strip">
      <div class="top-strip-inner">
        <router-link to="/login" class="nav-link">
          {{ $t('public_api.back_to_login') }}
        </router-link>
        <h1>{{ $t('public_api.ocr_demo_eyebrow') }}</h1>
        <router-link to="/public-api" class="docs-link">
          {{ $t('public_api.docs_link') }}
        </router-link>
      </div>
    </section>

    <section class="workspace">
      <div class="upload-panel">
        <input
          ref="fileInput"
          class="file-input"
          type="file"
          accept=".pdf,image/png,image/jpeg"
          @change="onFileChange"
        >
        <button type="button" class="upload-box" @click="chooseFile">
          <span class="upload-title">{{ $t('public_api.ocr_upload_title') }}</span>
          <span class="upload-hint">{{ selectedFile?.name || $t('public_api.ocr_upload_hint') }}</span>
        </button>
        <button
          type="button"
          class="run-button"
          :disabled="!selectedFile || isLoading"
          @click="submitOcr"
        >
          {{ isLoading ? $t('public_api.ocr_running') : $t('public_api.ocr_run') }}
        </button>
        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      </div>

      <div class="compare-grid">
        <div class="preview-panel">
          <div class="panel-header">
            <div>
              <h2>{{ $t('public_api.ocr_source_title') }}</h2>
              <p>{{ selectedFile?.name || $t('public_api.ocr_source_desc') }}</p>
            </div>
          </div>

          <div class="source-stage">
            <img
              v-if="filePreviewUrl && isImagePreview"
              :src="filePreviewUrl"
              class="source-image"
              alt=""
            >
            <object
              v-else-if="filePreviewUrl && isPdfPreview"
              :data="filePreviewUrl"
              type="application/pdf"
              class="source-pdf"
            >
              <a :href="filePreviewUrl" target="_blank" rel="noreferrer">
                {{ $t('public_api.ocr_open_file') }}
              </a>
            </object>
            <div v-else class="empty-state">
              {{ $t('public_api.ocr_empty_source') }}
            </div>
          </div>
        </div>

        <div class="preview-panel">
        <div class="panel-header">
          <div>
            <h2>{{ $t('public_api.ocr_preview_title') }}</h2>
            <p>{{ $t('public_api.ocr_preview_desc') }}</p>
          </div>
          <span class="token-count">{{ tokens.length }} {{ $t('public_api.ocr_tokens') }}</span>
        </div>

        <div class="preview-stage">
          <div v-if="!tokens.length" class="empty-state">
            {{ $t('public_api.ocr_empty_preview') }}
          </div>
          <template v-else>
            <span
              v-for="token in previewTokens"
              :key="token.id"
              class="ocr-token"
              :style="{ left: token.left, top: token.top }"
              :title="`x: ${token.x}, y: ${token.y}, score: ${token.score ?? '-'}`"
            >
              {{ token.text }}
            </span>
          </template>
        </div>
      </div>
      </div>

      <div class="texts-panel">
        <div class="panel-header compact">
          <h2>{{ $t('public_api.ocr_texts_title') }}</h2>
        </div>
        <ol v-if="texts.length" class="texts-list">
          <li v-for="(line, index) in texts" :key="`${index}-${line}`">{{ line }}</li>
        </ol>
        <p v-else class="muted">{{ $t('public_api.ocr_no_texts') }}</p>
      </div>
    </section>
  </main>
</template>

<style scoped>
.ocr-demo-page {
  min-height: 100vh;
  background: #eef6f8;
  color: #102a43;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.top-strip {
  border-bottom: 1px solid #d9e2ec;
  background: #ffffff;
}

.top-strip-inner {
  display: flex;
  max-width: 1180px;
  margin: 0 auto;
  padding: 0.85rem 1.25rem;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.nav-link,
.docs-link {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  border: 1px solid #bae6fd;
  border-radius: 7px;
  background: #f0f9ff;
  color: #0369a1;
  font-weight: 800;
  text-decoration: none;
}

.nav-link,
.docs-link {
  padding: 0.48rem 0.7rem;
  font-size: 0.82rem;
}

.nav-link:hover,
.docs-link:hover {
  border-color: #38bdf8;
  background: #e0f2fe;
}

.top-strip h1 {
  margin: 0;
  color: #102a43;
  font-size: 1.05rem;
  line-height: 1.16;
  letter-spacing: 0;
}

.workspace {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  max-width: 1180px;
  margin: 0 auto;
  padding: 1rem 1.25rem 2.5rem;
}

.upload-panel,
.preview-panel,
.texts-panel {
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  background: #fff;
}

.upload-panel {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) auto;
  align-items: stretch;
  gap: 0.85rem;
  padding: 1rem;
}

.file-input {
  display: none;
}

.upload-box {
  display: grid;
  gap: 0.45rem;
  min-height: 76px;
  padding: 1rem;
  border: 1px dashed #7dd3fc;
  border-radius: 8px;
  background: #f0fdfa;
  color: #0f766e;
  cursor: pointer;
  text-align: left;
}

.upload-title {
  font-size: 1rem;
  font-weight: 900;
}

.upload-hint {
  overflow-wrap: anywhere;
  color: #475569;
  line-height: 1.45;
}

.run-button {
  min-width: 132px;
  min-height: 76px;
  border: 0;
  border-radius: 7px;
  background: #0f766e;
  color: #fff;
  font-weight: 900;
  cursor: pointer;
}

.run-button:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.error-message {
  grid-column: 1 / -1;
  margin: 0;
  color: #b91c1c;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.compare-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 1rem;
}

.preview-panel {
  min-width: 0;
  padding: 1rem;
}

.source-stage,
.preview-stage {
  height: 560px;
}

.source-stage {
  display: grid;
  overflow: auto;
  place-items: center;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  background: #f8fafc;
}

.source-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.source-pdf {
  width: 100%;
  height: 100%;
  border: 0;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.85rem;
}

.panel-header.compact {
  margin-bottom: 0.45rem;
}

.panel-header h2 {
  margin: 0;
  color: #102a43;
  font-size: 1rem;
}

.panel-header p {
  margin: 0.28rem 0 0;
  color: #627d98;
  font-size: 0.86rem;
  line-height: 1.5;
}

.token-count {
  flex: 0 0 auto;
  border-radius: 999px;
  background: #e0f2fe;
  color: #075985;
  font-size: 0.78rem;
  font-weight: 900;
  padding: 0.35rem 0.6rem;
}

.preview-stage {
  position: relative;
  overflow: auto;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  background:
    linear-gradient(#f8fafc 1px, transparent 1px),
    linear-gradient(90deg, #f8fafc 1px, transparent 1px),
    #ffffff;
  background-size: 24px 24px;
}

.empty-state {
  display: grid;
  min-height: 100%;
  place-items: center;
  color: #829ab1;
  padding: 1rem;
  text-align: center;
}

.ocr-token {
  position: absolute;
  max-width: 260px;
  transform: translate(-1px, -1px);
  border: 1px solid rgba(14, 116, 144, 0.35);
  border-radius: 4px;
  background: rgba(236, 254, 255, 0.9);
  color: #0e7490;
  font-size: 0.78rem;
  font-weight: 800;
  line-height: 1.2;
  padding: 0.16rem 0.25rem;
  overflow-wrap: anywhere;
  box-shadow: 0 2px 5px rgba(15, 23, 42, 0.08);
}

.texts-panel {
  grid-column: 1 / -1;
  padding: 1rem;
}

.texts-list {
  display: grid;
  gap: 0.35rem;
  margin: 0;
  padding-left: 1.4rem;
  color: #334e68;
}

.texts-list li {
  line-height: 1.55;
}

.muted {
  margin: 0;
  color: #829ab1;
}

@media (max-width: 900px) {
  .top-strip-inner,
  .compare-grid,
  .upload-panel {
    grid-template-columns: 1fr;
  }

  .top-strip-inner {
    display: grid;
    align-items: start;
  }

  .source-stage,
  .preview-stage,
  .empty-state {
    min-height: 420px;
    height: 420px;
  }
}
</style>
