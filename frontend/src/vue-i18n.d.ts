import 'vue'
import type { Composer } from 'vue-i18n'

declare module 'vue' {
  interface ComponentCustomProperties {
    $t: Composer['t']
  }
}

export {}
