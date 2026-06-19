/**
 * 全域 API 工具
 * 自動加上 VITE_API_BASE 前綴
 * 自動附帶 Supabase access token 到 Authorization header
 */
import { supabase } from './supabase'

const getBaseURL = () => {
  return (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')
}

/**
 * 根據環境變數組合完整的 API URL
 * @param {string} path API 路徑，例如 '/auth/google/url'
 * @returns {string} 完整的 URL
 */
export function createApiUrl(path) {
  let baseURL = getBaseURL()
  if (!baseURL.endsWith('/api')) {
    baseURL += '/api'
  }
  return `${baseURL}${path}`
}

/**
 * 取得目前登入使用者的 Supabase access token (JWT)。
 * 沒登入或拿不到 session 時回傳 null。
 */
async function getAuthToken() {
  try {
    const { data } = await supabase.auth.getSession()
    return data?.session?.access_token || null
  } catch (err) {
    console.warn('[apiFetch] 取得 Supabase session 失敗:', err)
    return null
  }
}

/**
 * 全域 fetch 包裝，自動加上 API Base URL 與 Authorization header。
 * 注意：FormData 時不要設定 Content-Type，讓瀏覽器自動帶 boundary。
 * @param {string} path API 路徑
 * @param {object} options fetch 選項
 * @returns {Promise} fetch 結果
 */
export async function apiFetch(path, options = {}) {
  const url = createApiUrl(path)
  const headers = new Headers(options.headers || {})

  const token = await getAuthToken()
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  return fetch(url, { ...options, headers })
}
