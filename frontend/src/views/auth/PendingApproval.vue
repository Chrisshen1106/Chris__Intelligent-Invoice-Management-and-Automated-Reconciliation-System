<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { supabase } from '@/supabase.js'
import AuthLayout from './AuthLayout.vue'

const router = useRouter()
const { t } = useI18n()

const checking = ref(false)
const message = ref('')

async function recheck() {
  checking.value = true
  message.value = ''
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) {
    checking.value = false
    router.replace('/login')
    return
  }
  const { data: profile } = await supabase
    .from('profiles')
    .select('is_active')
    .eq('id', session.user.id)
    .maybeSingle()
  checking.value = false
  if (profile && profile.is_active) {
    // Approved — let the smart entry route resolve the role page.
    router.replace('/')
  } else {
    message.value = t('auth.pending_still_inactive')
  }
}

async function signOut() {
  await supabase.auth.signOut()
  router.replace('/login')
}
</script>

<template>
  <AuthLayout>
    <div class="pending-card">
      <div class="pending-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>
      </div>

      <h2 class="pending-title">{{ $t('auth.pending_title') }}</h2>
      <p class="pending-message">{{ $t('auth.pending_message') }}</p>

      <div v-if="message" class="pending-warning">{{ message }}</div>

      <button class="btn-primary" :disabled="checking" @click="recheck">
        {{ checking ? '...' : $t('auth.pending_recheck') }}
      </button>
      <button class="btn-secondary" @click="signOut">
        {{ $t('auth.pending_signout') }}
      </button>
    </div>
  </AuthLayout>
</template>

<style scoped>
.pending-card {
  width: 100%;
  text-align: center;
}
.pending-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  margin: 0 auto 1.25rem;
  border-radius: 50%;
  background: linear-gradient(135deg, #ecfeff 0%, #cffafe 100%);
  color: #0891b2;
  box-shadow: 0 4px 14px rgba(8, 145, 178, 0.18);
}
.pending-title {
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #0f172a;
  margin: 0 0 0.75rem;
}
.pending-message {
  font-size: 0.95rem;
  line-height: 1.6;
  color: #64748b;
  margin: 0 0 1.5rem;
}
.pending-warning {
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
  padding: 0.6rem 0.85rem;
  border-radius: 8px;
  font-size: 0.85rem;
  margin-bottom: 1rem;
  text-align: left;
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
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.2s ease, filter 0.2s ease;
  box-shadow: 0 4px 14px rgba(8, 145, 178, 0.35);
  margin-bottom: 0.6rem;
}
.btn-primary:hover:not(:disabled) {
  filter: brightness(1.05);
  box-shadow: 0 6px 20px rgba(8, 145, 178, 0.45);
  transform: translateY(-1px);
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-secondary {
  width: 100%;
  padding: 0.75rem 1rem;
  background: #fff;
  color: #334155;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.btn-secondary:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}
</style>
