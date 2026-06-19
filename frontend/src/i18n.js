import { createI18n } from 'vue-i18n'
import module_example_en from './locales/module_example/en.json'
import module_example_zhTW from './locales/module_example/zh-TW.json'
import admin_en from './locales/admin/en.json'
import admin_zhTW from './locales/admin/zh-TW.json'
import employee_en from './locales/employee/en.json'
import employee_zhTW from './locales/employee/zh-TW.json'
import finance_en from './locales/finance/en.json'
import finance_zhTW from './locales/finance/zh-TW.json'
import finance_mgr_en from './locales/finance_mgr/en.json'
import finance_mgr_zhTW from './locales/finance_mgr/zh-TW.json'
import auth_en from './locales/auth/en.json'
import auth_zhTW from './locales/auth/zh-TW.json'
import public_api_en from './locales/public_api/en.json'
import public_api_zhTW from './locales/public_api/zh-TW.json'

const i18n = createI18n({
  legacy: false, // Composition API is standard
  globalInjection: true,
  locale: 'zh-TW',
  fallbackLocale: 'en',
  messages: {
    en: {
      module_example: module_example_en,
      admin: admin_en,
      employee: employee_en,
      finance: finance_en,
      finance_mgr: finance_mgr_en,
      auth: auth_en,
      public_api: public_api_en
    },
    'zh-TW': {
      module_example: module_example_zhTW,
      admin: admin_zhTW,
      employee: employee_zhTW,
      finance: finance_zhTW,
      finance_mgr: finance_mgr_zhTW,
      auth: auth_zhTW,
      public_api: public_api_zhTW
    }
  }
})

export default i18n
