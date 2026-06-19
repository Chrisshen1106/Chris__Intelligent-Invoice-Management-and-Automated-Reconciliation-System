<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useI18n } from 'vue-i18n'

// AuthLayout: split layout used by /login, /register and /auth/pending.
// Left  : brand panel with auto-rotating carousel (3 cards) + dots.
// Right : <slot /> for the actual auth form.
// RWD   : < 1024px stacks vertically; on mobile the carousel stops and
//         only the first card is shown to keep the auth form prominent.

const { t } = useI18n()

const cards = computed(() => [
  { title: t('auth.card1_title'), desc: t('auth.card1_desc') },
  { title: t('auth.card2_title'), desc: t('auth.card2_desc') },
  { title: t('auth.card3_title'), desc: t('auth.card3_desc') }
])

const currentIndex = ref(0)
const paused = ref(false)
const isMobile = ref(false)
const INTERVAL_MS = 5000
let timerId = null

function startTimer() {
  stopTimer()
  if (isMobile.value) return
  timerId = setInterval(() => {
    if (!paused.value) {
      currentIndex.value = (currentIndex.value + 1) % cards.value.length
    }
  }, INTERVAL_MS)
}
function stopTimer() {
  if (timerId !== null) {
    clearInterval(timerId)
    timerId = null
  }
}
function goTo(idx) {
  currentIndex.value = idx
  // Reset the timer so the user has the full interval to read after clicking.
  startTimer()
}

function updateIsMobile() {
  isMobile.value = window.innerWidth < 1024
}

onMounted(() => {
  updateIsMobile()
  window.addEventListener('resize', updateIsMobile)
  startTimer()
})
onBeforeUnmount(() => {
  stopTimer()
  window.removeEventListener('resize', updateIsMobile)
})
</script>

<template>
  <div class="auth-layout">
    <!-- Left brand panel -->
    <aside class="auth-brand">
      <div class="brand-inner">
        <div class="brand-logo">
          <img src="/iimars-icon.png" alt="" class="brand-logo-icon">
          <span>IIMARS</span>
        </div>
        <h1 class="brand-title">{{ $t('auth.brand_tagline') }}</h1>

        <!-- Carousel -->
        <div
          class="carousel"
          @mouseenter="paused = true"
          @mouseleave="paused = false"
        >
          <div class="carousel-stage">
            <transition name="fade" mode="out-in">
              <div
                :key="currentIndex"
                class="carousel-card"
              >
                <div class="card-title">{{ cards[currentIndex].title }}</div>
                <p class="card-desc">{{ cards[currentIndex].desc }}</p>
              </div>
            </transition>
          </div>
          <div class="carousel-dots" v-if="!isMobile">
            <button
              v-for="(card, idx) in cards"
              :key="idx"
              type="button"
              class="dot"
              :class="{ active: idx === currentIndex }"
              :aria-label="`Show card ${idx + 1}`"
              @click="goTo(idx)"
            ></button>
          </div>
        </div>

        <div class="brand-footer">
          <div class="public-actions">
            <router-link to="/public-api" class="public-action-link" target="_blank">
              {{ $t('public_api.docs_link') }}
            </router-link>
            <router-link to="/public-ocr-demo" class="public-action-link" target="_blank">
              {{ $t('public_api.ocr_demo_link') }}
            </router-link>
          </div>
        </div>
      </div>
    </aside>

    <!-- Right form panel -->
    <main class="auth-form-panel">
      <div class="auth-form-inner">
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
.auth-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 100vh;
  background: #f8fafc;
  font-family: 'Inter', -apple-system, sans-serif;
}

/* ---- Left brand panel (Ocean Mint) ---- */
.auth-brand {
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle at 20% 20%, rgba(20, 184, 166, 0.45) 0%, transparent 45%),
    radial-gradient(circle at 85% 75%, rgba(8, 145, 178, 0.55) 0%, transparent 50%),
    linear-gradient(135deg, #0c4a6e 0%, #0e7490 45%, #14b8a6 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem 2.5rem;
}
/* Faint grid overlay */
.auth-brand::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.06) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(circle at center, #000 30%, transparent 75%);
  -webkit-mask-image: radial-gradient(circle at center, #000 30%, transparent 75%);
  pointer-events: none;
}
/* Decorative blurred orb */
.auth-brand::after {
  content: '';
  position: absolute;
  top: -120px;
  right: -120px;
  width: 360px;
  height: 360px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(125, 211, 252, 0.55) 0%, transparent 70%);
  filter: blur(20px);
  pointer-events: none;
}
.brand-inner {
  position: relative;
  z-index: 1;
  max-width: 460px;
  width: 100%;
  padding-right: 4.5rem;
}
.brand-logo {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  margin-bottom: 2.25rem;
  padding: 0.4rem 0.85rem 0.4rem 0.55rem;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  backdrop-filter: blur(6px);
}

.brand-logo-icon {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  object-fit: cover;
  box-shadow: 0 4px 12px rgba(94, 234, 212, 0.5);
}
.brand-title {
  font-size: 2.25rem;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.01em;
  margin: 0 0 2.25rem;
  text-shadow: 0 2px 20px rgba(0, 0, 0, 0.15);
}

/* ---- Carousel ---- */
.carousel {
  margin-bottom: 2.5rem;
}
.carousel-stage {
  position: relative;
  min-height: 140px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 14px;
  padding: 1.4rem 1.5rem;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.2),
    0 8px 30px rgba(8, 47, 73, 0.25);
}
.carousel-card {
  width: 100%;
}
.card-title {
  font-size: 1.05rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}
.card-desc {
  font-size: 0.92rem;
  line-height: 1.55;
  opacity: 0.9;
  margin: 0;
}

.carousel-dots {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 1rem;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: none;
  padding: 0;
  background: rgba(255, 255, 255, 0.35);
  cursor: pointer;
  transition: background 0.2s, transform 0.2s;
}
.dot:hover {
  background: rgba(255, 255, 255, 0.6);
}
.dot.active {
  background: #fff;
  transform: scale(1.2);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.4s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.brand-footer {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  align-items: flex-start;
}

.public-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  max-width: 330px;
  padding-right: 3rem;
}

.public-action-link {
  display: inline-flex;
  align-items: center;
  padding: 0.45rem 0.7rem;
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  color: #ecfeff;
  font-size: 0.82rem;
  font-weight: 700;
  text-decoration: none;
  backdrop-filter: blur(8px);
  transition: background 0.15s, border-color 0.15s, transform 0.15s;
}
.public-action-link:hover {
  background: rgba(255, 255, 255, 0.16);
  border-color: rgba(255, 255, 255, 0.4);
  transform: translateY(-1px);
}

/* ---- Right form panel ---- */
.auth-form-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
}
.auth-form-inner {
  width: 100%;
  max-width: 400px;
}

/* ---- RWD ---- */
@media (max-width: 1023px) {
  .auth-layout {
    grid-template-columns: 1fr;
  }
  .auth-brand {
    padding: 2rem 1.5rem;
  }
  .brand-inner {
    max-width: 100%;
    padding-right: 0;
  }
  .brand-title {
    font-size: 1.5rem;
    margin-bottom: 1.25rem;
  }
  .carousel {
    margin-bottom: 1rem;
  }
  .carousel-stage {
    min-height: auto;
  }
  .auth-form-panel {
    padding: 2rem 1.25rem 3rem;
  }
  .brand-footer {
    gap: 0.45rem;
  }
}
@media (max-width: 480px) {
  .card-title {
    font-size: 1rem;
  }
  .card-desc {
    font-size: 0.88rem;
  }
}
</style>
