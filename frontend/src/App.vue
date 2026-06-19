<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { supabase } from './supabase.js'

const router = useRouter()
const route = useRoute()
const { locale } = useI18n()

const user = ref(null)
const isLoading = ref(true)

// Auth pages hide the main header but keep a floating language switcher.
const isAuthPage = computed(() => {
  return ['/login', '/register', '/auth/callback', '/auth/pending', '/public-api', '/public-ocr-demo'].includes(route.path)
})
const hideHeader = isAuthPage

function switchLocale(event) {
  locale.value = event.target.value
}

async function logout() {
  await supabase.auth.signOut()
  user.value = null
  router.replace('/login')
}

onMounted(() => {
  supabase.auth.getSession().then(({ data: { session } }) => {
    user.value = session?.user ?? null
    isLoading.value = false
  })

  supabase.auth.onAuthStateChange((event, session) => {
    user.value = session?.user ?? null
    if (event === 'SIGNED_OUT') {
      router.replace('/login')
    }
  })
})
</script>

<template>
  <div class="app-container">
    <header v-if="!hideHeader" class="app-header">
      <div class="header-left">
        <router-link to="/" class="brand-link">
          <img src="/iimars-icon.png" alt="" class="brand-icon">
          <span>IIMARS</span>
        </router-link>
      </div>
      <div class="header-right">
        <div v-if="user" class="user-info">
          <img
            v-if="user.user_metadata?.avatar_url"
            :src="user.user_metadata.avatar_url"
            class="user-avatar"
            referrerpolicy="no-referrer"
          />
          <span class="user-name">{{ user.user_metadata?.full_name || user.email }}</span>
          <button class="logout-btn" @click="logout">{{ $t('module_example.logout') }}</button>
        </div>
        <div class="language-switcher">
          <select @change="switchLocale" :value="locale">
            <option value="en">English</option>
            <option value="zh-TW">繁體中文</option>
          </select>
        </div>
      </div>
    </header>

    <main :class="{ 'main-with-header': !hideHeader }">
      <router-view />
    </main>

    <!-- Floating language switcher on auth pages -->
    <div v-if="isAuthPage" class="floating-lang">
      <select @change="switchLocale" :value="locale">
        <option value="en">English</option>
        <option value="zh-TW">繁體中文</option>
      </select>
    </div>
  </div>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  font-family: 'Inter', -apple-system, sans-serif;
}

.brand-link {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 1rem;
  font-weight: 700;
  color: #1e293b;
  text-decoration: none;
}

.brand-icon {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  object-fit: cover;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
}

.user-name {
  font-size: 0.9rem;
  color: #334155;
}

.logout-btn {
  padding: 0.4rem 0.85rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.85rem;
  color: #334155;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.logout-btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.language-switcher select {
  padding: 0.35rem 0.6rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #fff;
  font-size: 0.85rem;
  color: #334155;
  cursor: pointer;
}

main {
  flex: 1;
}

.floating-lang {
  position: fixed;
  top: 1.25rem;
  right: 1.25rem;
  z-index: 50;
}
.floating-lang select {
  padding: 0.4rem 0.7rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #fff;
  color: #1e293b;
  font-size: 0.85rem;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}
.floating-lang select:hover {
  border-color: #cbd5e1;
}
</style>
