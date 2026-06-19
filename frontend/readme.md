# Frontend Project

本專案使用 Vue 3 + Vite 進行開發，並整合了 Vue Router 與 Vue I18n (Composition API Mode) 以支援多語系開發。

## 架構重點

目前前端的 API 呼叫與登入導向，主要由下列三個設定控制：

- `VITE_API_BASE`：API 基底路徑，供前端組合所有 `/api/...` 請求。
- `VITE_API_MOCK_ENABLED`：是否啟用 MSW mock 服務。
- `disableAccessManagement`：是否暫時關閉使用者角色導向與權限管理流程。

實作上，前端仍以 `/api/...` 的路徑撰寫請求，實際送出時由環境變數與開發代理處理，因此程式碼不需要在各個頁面重複改寫 API 網址。

## 快速開始 (Quick Start)

請依照以下終端機指令 (cmd command) 將專案 clone 到本機並啟動開發伺服器：

1. **Clone 專案並進入開發資料夾** (請將 `<YOUR_REPO_URL>` 替換為實際的 Git 網址)：
   ```cmd
   git clone <YOUR_REPO_URL>
   cd project/frontend
   ```

2. **安裝依賴套件** (需確認環境已安裝 Node.js 與 npm)：
   ```cmd
   npm install
   ```

3. **啟動開發伺服器**：
   ```cmd
   npm run dev
   ```

伺服器成功啟動後，請依據終端機顯示的本機網址 (通常為 `http://localhost:5173/`)，在瀏覽器中開啟服務。

## 環境變數設定

本專案使用 Vite 的環境變數機制管理 API 與 mock 行為。請在專案根目錄的環境檔中設定：

- `.env`：放共用設定。
- `.env.development`：開發環境覆寫設定。
- `.env.production`：正式環境覆寫設定。

### `VITE_API_BASE`

API 基底路徑。前端以此值組合 API 請求路徑。

範例：

```env
VITE_API_BASE=/api
```

如果後端已由反向代理或 Vite proxy 提供 `/api`，通常保持 `/api` 即可。

### `VITE_API_MOCK_ENABLED`

控制是否在啟動前載入 MSW mock server。

- `true`：啟用 mock。
- `false`：停用 mock，改走實際後端 API。

這個值通常只需要放在 `.env` 做共用設定，除非你想針對特定環境覆蓋。

範例：

```env
VITE_API_MOCK_ENABLED=true
```

### 環境檔建議

```env
# .env
VITE_API_MOCK_ENABLED=true

# .env.development
VITE_API_BASE=/api

# .env.production
VITE_API_BASE=/api
```

Vite 會依執行模式自動載入對應環境檔，優先順序為：模式專屬檔案覆蓋共用檔案。

## 權限管理說明

`src/App.vue` 內的 `disableAccessManagement` 目前用來控制首頁登入後是否啟用角色導向與帳號狀態檢查。

- `true`：停用權限管理流程，登入後不會根據 `profiles.role_code` 自動導向對應頁面。
- `false`：啟用權限管理流程，系統會依據使用者 `profiles` 資料決定導向路由，並處理未註冊或停用帳號的情況。

目前專案將它設為 `true`，表示此功能先保留程式，但暫不強制啟用。若未來要恢復角色導向，只要改成 `false` 即可。

## 檔案結構 (Project Structure)

本專案基於典型的 Vue 結構，並已建立好指定的範例模組 (`module_example`) 的詳細檔案分層：

```text
frontend/
├── .env                     # 共用環境變數
├── .env.development         # 開發環境變數
├── .env.production          # 正式環境變數
├── src/
│   ├── locales/
│   │   └── module_example/     # module_example 的專屬多語系檔案
│   │       ├── en.json         # 英文翻譯
│   │       └── zh-TW.json      # 繁體中文翻譯
│   ├── router/
│   │   ├── index.js            # Router 主設定，彙整與載入各個模組
│   │   └── module_example.js   # module_example 內的所有專屬路由
│   ├── views/
│   │   └── module_example/
│   │       └── Index.vue       # module_example 的檢視畫面/元件
│   ├── App.vue                 # 根組件 (包含 router-view 與多語系切換器)
│   ├── i18n.js                 # Vue-i18n 的實例建立與設定檔
│   └── main.js                 # Vue 進入點 (掛載 app, i18n, router)
├── package.json                # npm 專案與依賴管理檔
└── vite.config.js              # Vite 建置相關設定檔
```

### 多語系開發相關提示
- **i18n ally**: 結構與配置方式已完美支援 VS Code 的 i18n ally 擴充套件。我們建議您安裝此擴充套件，它可以自動讀取 `src/locales` 目錄並提供更好的開發者翻譯預覽體驗。
