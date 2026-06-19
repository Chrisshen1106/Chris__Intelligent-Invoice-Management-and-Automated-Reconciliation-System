<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { supabase } from '../supabase.js'

const router = useRouter()
const { t } = useI18n()

const errorMsg = ref('')
const isLoading = ref(true)
const showInactiveBanner = ref(false)
let handled = false

const disableAccessManagement = import.meta.env.VITE_DISABLE_ACCESS_MANAGEMENT === 'true'
const DEFAULT_AUTHENTICATED_ROUTE = '/employee-dashboard'

// role_code → route 對照（對應 profiles 表的 role_code 欄位）
// G=訪客, E=一般員工, A=會計, M=財務主管, AD=系統管理員
const roleRouteMap = {
  E: '/employee-dashboard',
  A: '/finance',
  M: '/finance-manager',
  AD: '/admin'
}

async function handleSession(session) {
  if (handled) return
  handled = true

  if (!session) {
    isLoading.value = false
    errorMsg.value = t('module_example.account_not_registered')
    return
  }

  const user = session.user
  console.log('[AuthCallback] user.id:', user.id)
  console.log('[AuthCallback] user.email:', user.email)

  try {
    // 查詢 profiles 表取得 role_code
    console.log('[AuthCallback] querying profiles table...')
    const { data: profile, error: profileError } = await supabase
      .from('profiles')
      .select('role_code, is_active')
      .eq('id', user.id)
      .maybeSingle()

    console.log('[AuthCallback] profile:', JSON.stringify(profile))
    console.log('[AuthCallback] profileError:', JSON.stringify(profileError))

    if (profileError || !profile) {
      // 帳號不在 profiles 裡 → 尚未註冊
      // dev mode: fall through to default route so OAuth users can still test.
      if (disableAccessManagement) {
        router.replace(DEFAULT_AUTHENTICATED_ROUTE)
        return
      }
      isLoading.value = false
      errorMsg.value = t('module_example.account_not_registered')
      return
    }

    // 帳號尚未啟用（Admin 尚未核准）→ 導到 /auth/pending
    // dev mode: skip the inactive gate so QA can iterate freely.
    if (!profile.is_active && !disableAccessManagement) {
      router.replace('/auth/pending')
      return
    }

    const targetRoute = roleRouteMap[profile.role_code]
    console.log('[AuthCallback] role_code:', profile.role_code, '→ route:', targetRoute)
    if (targetRoute) {
      router.replace(targetRoute)
    } else if (disableAccessManagement) {
      // Unknown / null role_code in dev: fall back to default route.
      router.replace(DEFAULT_AUTHENTICATED_ROUTE)
    } else {
      isLoading.value = false
      errorMsg.value = t('module_example.account_not_registered')
    }
  } catch (err) {
    console.error('[AuthCallback] unexpected error:', err)
    isLoading.value = false
    errorMsg.value = t('module_example.account_not_registered')
  }
}

onMounted(() => {
  // 監聽 auth 狀態變化 — OAuth 回調時 Supabase 會先處理 URL hash，
  // 處理完後觸發 SIGNED_IN 事件，這時才能拿到正確的 session
  const { data: { subscription } } = supabase.auth.onAuthStateChange(
    async (event, session) => {
      if (event === 'SIGNED_IN' || event === 'INITIAL_SESSION') {
        if (session) {
          await handleSession(session)
          subscription.unsubscribe()
        }
      }
    }
  )

  // 如果已有 session（例如已登入狀態重新訪問此頁），也直接處理
  supabase.auth.getSession().then(({ data: { session } }) => {
    if (session) {
      handleSession(session)
    }
  })

  // 超時保護：10 秒後若仍未取得 session，顯示錯誤
  setTimeout(() => {
    if (isLoading.value) {
      isLoading.value = false
      errorMsg.value = t('module_example.account_not_registered')
    }
  }, 10000)
})

async function handleLogout() {
  await supabase.auth.signOut()
  router.replace('/login')
}

async function closeBanner() {
  await supabase.auth.signOut()
  router.replace('/login')
}

</script>

<template>
  <div class="callback-container">
    <div v-if="isLoading" class="loading-state">
      <div class="spinner"></div>
      <p>{{ $t('module_example.logging_in') }}</p>
    </div>
    <div v-else-if="showInactiveBanner" class="inactive-banner">
      <p class="banner-msg">{{ $t('module_example.account_not_activated') }}</p>
      <button class="banner-close-btn" @click="closeBanner">OK</button>
    </div>
    <div v-else class="error-state">
      <div class="error-icon">!</div>
      <p class="error-msg">{{ errorMsg }}</p>
      <button class="back-btn" @click="handleLogout">{{ $t('module_example.logout') }}</button>
    </div>
  </div>
</template>

<style scoped>
.callback-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  font-size: 1.2rem;
  color: #475569;
}
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}
.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  text-align: center;
}
.error-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #fee2e2;
  color: #dc2626;
  font-size: 1.5rem;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}
.error-msg {
  color: #dc2626;
  font-weight: 600;
  font-size: 1.1rem;
}
.back-btn {
  padding: 0.5rem 1.5rem;
  border-radius: 8px;
  background: #f1f5f9;
  border: 1.5px solid #e2e8f0;
  color: #475569;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}
.back-btn:hover {
  background: #e2e8f0;
}
.inactive-banner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  text-align: center;
  background: #fffbeb;
  border: 1.5px solid #f59e0b;
  border-radius: 12px;
  padding: 2.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
.banner-msg {
  color: #92400e;
  font-weight: 600;
  font-size: 1.1rem;
  margin: 0;
}
.banner-close-btn {
  padding: 0.5rem 1.5rem;
  border-radius: 8px;
  background: #f59e0b;
  border: none;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}
.banner-close-btn:hover {
  background: #d97706;
}
</style>
