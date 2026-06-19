<script setup>
import { computed, onMounted } from 'vue'

function defaultSwaggerDocsUrl() {
  if (window.location.port === '5173') {
    return 'http://localhost:8000/api/public/docs'
  }

  return `${window.location.origin}/api/public/docs`
}

const swaggerDocsUrl = computed(() => {
  return import.meta.env.VITE_SWAGGER_DOCS_URL || defaultSwaggerDocsUrl()
})

onMounted(() => {
  window.location.replace(swaggerDocsUrl.value)
})
</script>

<template>
  <main class="redirect-page">
    <div class="redirect-panel">
      <p>Redirecting to public Swagger docs...</p>
      <a :href="swaggerDocsUrl">Open Swagger</a>
    </div>
  </main>
</template>

<style scoped>
.redirect-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  background: #f8fafc;
  color: #0f172a;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.redirect-panel {
  display: grid;
  gap: 0.75rem;
  justify-items: center;
  padding: 1.25rem;
}

.redirect-panel p {
  margin: 0;
  color: #475569;
}

.redirect-panel a {
  color: #0369a1;
  font-weight: 800;
  text-decoration: none;
}

.redirect-panel a:hover {
  text-decoration: underline;
}
</style>
