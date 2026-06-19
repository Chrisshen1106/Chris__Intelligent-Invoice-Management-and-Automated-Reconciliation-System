# 前後端分離 Container 部署注意事項

本文說明當前端與後端部署在不同 container 時，前端需要特別注意的環境變數與相關設定。重點是：`VITE_*` 參數會在前端建置時寫入 bundle，並不是執行時再讀取，因此只改 container 啟動環境但不重新建置，通常不會生效。

## 部署前先確認的前提

- 前端 container 只負責輸出靜態資源，瀏覽器會直接讀取前端 bundle。
- 後端 container 需要提供可被瀏覽器連到的 API 入口，或由反向代理統一轉發 `/api`。
- `frontend/vite.config.js` 內的 `server.proxy` 只影響本機開發模式，正式部署不會自動套用。

## 1. `VITE_API_BASE`

### 作用

前端所有 API 都是透過 [frontend/src/api.js](../frontend/src/api.js) 組出完整路徑。`createApiUrl()` 會把 `VITE_API_BASE` 加到每個請求前面，因此 API 路徑仍建議維持寫成 `/xxx` 的相對路徑。

### 建議設定

- 同網域、由反向代理統一轉發時：保留 `/api`
- 前端與後端不同網域時：設定成後端可直接存取的完整網址前綴，例如 `https://api.example.com`
- 若是 Docker Compose 內部網路，瀏覽器端無法解析容器名稱；前端 bundle 仍要指向使用者瀏覽器可連到的網址，而不是 container hostname

### 範例

```env
VITE_API_BASE=/api
```

或

```env
VITE_API_BASE=https://api.example.com
```

### 注意事項

- 末尾不要多一個 `/`，程式雖會去掉 `VITE_API_BASE` 結尾斜線，但仍建議統一寫法。
- `VITE_API_BASE` 是 build-time 參數，修改後要重新 build 前端 image。
- 目前 `frontend/vite.config.js` 的 dev proxy 只是本機開發用，正式環境是否能走 `/api`，要看你實際的 Nginx / Ingress / API Gateway 設定。

## 2. `VITE_API_MOCK_ENABLED`

### 作用

這個參數在 [frontend/src/main.js](../frontend/src/main.js) 中被讀取。當值為 `true` 時，會在 Vue app mount 前載入 [frontend/src/mocks/browser.js](../frontend/src/mocks/browser.js)，由 MSW 攔截 API 請求。

### 建議設定

- 本機開發或 mock 測試：`true`
- 正式環境與實際後端串接：`false`

### 範例

```env
VITE_API_MOCK_ENABLED=false
```

### 注意事項

- 若忘記關閉，前端可能會持續吃 mock 回應，導致看起來「後端有起來但前端沒有打到」。
- 這個值是在 app 啟動前判斷一次，因此改完後需要重新 build 或至少重新啟動前端服務。
- `public/mockServiceWorker.js` 必須存在，mock 才能正常啟動。

## 3. `VITE_DISABLE_ACCESS_MANAGEMENT`

### 作用

這個環境變數控制是否停用登入後的權限管理與角色導向。目前在 [frontend/src/App.vue](../frontend/src/App.vue) 與 [frontend/src/router/index.js](../frontend/src/router/index.js) 中會讀取此變數。

- 在 `App.vue` 中，它控制登入後是否依 `profiles.role_code` 自動導向對應頁面
- 在 `router/index.js` 中，它控制 route guard 是否檢查登入狀態與角色權限

### 建議設定

- `true`：停用登入後的角色導向與權限檢查
- `false`：啟用 Supabase session 檢查、`profiles` 查詢，以及角色限制路由保護

### 範例

```env
VITE_DISABLE_ACCESS_MANAGEMENT=false
```

### 注意事項

- 如果正式環境要啟用角色權限，請將其設定為 `false`。由於它是 build-time 參數，修改後需要重新 build 前端 image 才會生效。

### 啟用後的依賴條件

當權限管理啟用（設定為 `false`）時，系統會依賴 Supabase 的 `profiles` 資料：

- `id`
- `role_code`
- `is_active`

若資料不完整，登入後導向與權限判斷會失敗。

## 4. 其他重要可調參數

### `import.meta.env.BASE_URL`

路由建立使用 [frontend/src/router/index.js](../frontend/src/router/index.js) 的 `createWebHistory(import.meta.env.BASE_URL)`。

- 若前端掛在根目錄，通常不需要特別處理
- 若前端部署在子路徑，例如 `https://example.com/app/`，需要同步調整 Vite 的 base 設定，否則路由刷新會 404

### `vite.config.js` 的開發代理

`frontend/vite.config.js` 目前把 `/api` 代理到 `http://127.0.0.1:8000`。

- 只影響 `npm run dev`
- 不影響 `npm run build` 後的正式部署
- 若後端開發 port 改了，這裡也要一起改

### Supabase 連線資訊

[frontend/src/supabase.js](../frontend/src/supabase.js) 目前把 Supabase URL 與 anon key 寫死在程式內。

- 若要切換測試 / 正式 Supabase 專案，需要改程式並重新 build
- 若要更好地管理多環境，建議改成環境變數

### API 入口的跨網域設定

如果前後端不是同網域，除了 `VITE_API_BASE` 以外，後端還要確認：

- CORS 是否允許前端 origin
- Cookie / Session 是否符合跨站設定需求
- 若有反向代理，路由是否正確轉發 `/api`

## 建議的環境檔組合

### 方案 A：同網域反向代理

```env
# .env
VITE_API_MOCK_ENABLED=false

# .env.production
VITE_API_BASE=/api
```

適合前端與後端都掛在同一個對外網域，由 Nginx / Ingress / API Gateway 統一轉發。

### 方案 B：前後端不同網域

```env
# .env
VITE_API_MOCK_ENABLED=false

# .env.production
VITE_API_BASE=https://api.example.com
```

適合前端與後端完全分開部署，且後端 API 有獨立公開網址。

## 最後檢查清單

- 前端是否已重新 build，讓最新的 `VITE_API_*` 生效
- `VITE_API_MOCK_ENABLED` 是否已關閉
- `VITE_DISABLE_ACCESS_MANAGEMENT` 是否符合正式權限策略
- `VITE_API_BASE` 是否指向瀏覽器可直接連到的 API 入口
- 若前端部署在子路徑，`BASE_URL` 與伺服器 rewrite 是否一致
- 若啟用角色管理，Supabase `profiles` 資料是否完整