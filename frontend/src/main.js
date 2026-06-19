import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import { createApiUrl, apiFetch } from './api.js'

async function bootstrap() {
  if (import.meta.env.VITE_API_MOCK_ENABLED === 'true') {
    const { enableMocking } = await import('./mocks/browser.js')
    await enableMocking()
  }

  const app = createApp(App)
  app.use(router)
  app.use(i18n)
  
  // 全域註冊 API 工具（供新程式碼使用）
  app.config.globalProperties.$apiUrl = createApiUrl
  app.config.globalProperties.$apiFetch = apiFetch

  app.mount('#app')
}

bootstrap()
