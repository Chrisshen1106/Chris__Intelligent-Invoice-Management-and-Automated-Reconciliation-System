<script setup>
/**
 * Login.vue - 登入頁面
 * 職責：
 * 1. 提供登入表單 UI（郵箱/密碼、Google OAuth）
 * 2. 處理郵箱和 OAuth 登入邏輯
 * 3. 驗證帳號狀態（啟用/未啟用）
 * 4. 登入成功後直接路由到角色對應的儀表板
 * 5. 顯示登入錯誤訊息
 * 
 * 不涉及全局應用狀態管理 — 由 App.vue 處理
 * 認證成功後由路由系統接管，App.vue 監聽狀態變化
 */
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { supabase } from '../../supabase.js'
import AuthLayout from './AuthLayout.vue'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()

const email = ref('')
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)

// 角色與儀表板路由對應（同步 router/index.js 的 roleRouteMap）
const ROLE_ROUTE_MAP = {
  'E': '/employee-dashboard',    // 員工
  'A': '/finance',               // 會計
  'M': '/finance-manager',       // 財務主管
  'AD': '/admin'                 // 系統管理員
}

async function loginWithGoogle() {
  errorMsg.value = ''
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: `${window.location.origin}/auth/callback` }
  })
  if (error) errorMsg.value = error.message
}

/**
 * 郵箱/密碼登入 - 核心登入邏輯
 */
async function loginWithEmail() {
  if (!email.value || !password.value) {
    errorMsg.value = t('auth.login_error')
    return
  }
  errorMsg.value = ''
  loading.value = true
  
  // 1. 使用郵箱/密碼驗證
  const { error } = await supabase.auth.signInWithPassword({
    email: email.value,
    password: password.value
  })
  if (error) {
    loading.value = false
    errorMsg.value = error.message
    return
  }

  // 2. 檢查帳號是否已啟用（僅在啟用訪問管理時）
  const disableAccessManagement = import.meta.env.VITE_DISABLE_ACCESS_MANAGEMENT === 'true'
  const { data: { session } } = await supabase.auth.getSession()
  
  if (!disableAccessManagement && session) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('is_active, role_code')
      .eq('id', session.user.id)
      .maybeSingle()
    if (profile && !profile.is_active) {
      loading.value = false
      router.replace('/auth/pending')
      return
    }
  }

  loading.value = false
  
  // 3. 重定向到原始請求頁面（如果有 next 查詢參數）
  if (typeof route.query.next === 'string') {
    router.replace(route.query.next)
    return
  }

  // 4. 根據角色路由到對應的儀表板
  if (!disableAccessManagement && session) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('role_code')
      .eq('id', session.user.id)
      .maybeSingle()
    
    if (profile && ROLE_ROUTE_MAP[profile.role_code]) {
      router.replace(ROLE_ROUTE_MAP[profile.role_code])
      return
    }
  }
  
  // 開發模式或角色無法識別時，回退到根路徑
  // App.vue 的 beforeEnter 會負責最終路由
  router.replace('/')
}

function goRegister() {
  router.push('/register')
}
</script>

<template>
  <AuthLayout>
    <div class="login-card">
      <h2 class="login-title">{{ $t('auth.sign_in_title') }}</h2>
      <p class="login-subtitle">{{ $t('auth.welcome_back') }}</p>

      <button
        type="button"
        class="btn-google"
        @click="loginWithGoogle"
        :disabled="loading"
      >
        <svg class="google-icon" viewBox="0 0 24 24" width="18" height="18">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.27-4.74 3.27-8.1z"/>
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
        {{ $t('auth.continue_with_google') }}
      </button>

      <div class="divider"><span>{{ $t('auth.or') }}</span></div>

      <form class="login-form" @submit.prevent="loginWithEmail">
        <label class="field">
          <span>{{ $t('auth.email') }}</span>
          <input
            type="email"
            v-model="email"
            autocomplete="email"
            :disabled="loading"
          />
        </label>
        <label class="field">
          <span>{{ $t('auth.password') }}</span>
          <input
            type="password"
            v-model="password"
            autocomplete="current-password"
            :disabled="loading"
          />
        </label>

        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

        <button type="submit" class="btn-primary" :disabled="loading">
          {{ loading ? '...' : $t('auth.sign_in') }}
        </button>
      </form>

      <div class="login-footer">
        <span>{{ $t('auth.no_account_question') }}</span>
        <a href="#" @click.prevent="goRegister">{{ $t('auth.register_account') }}</a>
      </div>

    </div>
  </AuthLayout>
</template>

<style scoped>
.login-card {
  width: 100%;
}
.login-title {
  font-size: 1.95rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #0f172a;
  margin: 0 0 0.5rem;
}
.login-subtitle {
  font-size: 0.95rem;
  color: #64748b;
  margin: 0 0 1.9rem;
}

.btn-google {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  padding: 0.75rem 1rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 500;
  color: #1e293b;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.btn-google:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #cbd5e1;
}
.btn-google:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.divider {
  display: flex;
  align-items: center;
  text-align: center;
  margin: 1.5rem 0;
  color: #94a3b8;
  font-size: 0.85rem;
}
.divider::before,
.divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid #e2e8f0;
}
.divider span {
  padding: 0 0.75rem;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.field span {
  font-size: 0.85rem;
  font-weight: 500;
  color: #334155;
}
.field input {
  padding: 0.65rem 0.85rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.field input:focus {
  border-color: #0891b2;
  box-shadow: 0 0 0 3px rgba(8, 145, 178, 0.18);
}

.error-msg {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  padding: 0.6rem 0.85rem;
  border-radius: 8px;
  font-size: 0.85rem;
}

.btn-primary {
  width: 100%;
  padding: 0.8rem 1rem;
  background: linear-gradient(135deg, #0891b2 0%, #14b8a6 100%);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 0.98rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.2s ease, filter 0.2s ease;
  box-shadow: 0 4px 14px rgba(8, 145, 178, 0.35);
  margin-top: 0.25rem;
}
.btn-primary:hover:not(:disabled) {
  filter: brightness(1.05);
  box-shadow: 0 6px 20px rgba(8, 145, 178, 0.45);
  transform: translateY(-1px);
}
.btn-primary:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 3px 10px rgba(8, 145, 178, 0.3);
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-footer {
  margin-top: 1.5rem;
  text-align: center;
  font-size: 0.88rem;
  color: #64748b;
}
.login-footer a {
  margin-left: 0.4rem;
  color: #0891b2;
  font-weight: 600;
  text-decoration: none;
}
.login-footer a:hover {
  text-decoration: underline;
}

</style>
