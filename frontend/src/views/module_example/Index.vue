<template>
  <div class="module-example">
    <h1>{{ $t('module_example.welcome') }}</h1>
    <p>{{ $t('module_example.hello') }}{{ $t('module_example.vite_vue') }}</p>
  </div>
</template>

<style scoped>
.module-example {
  padding: 20px;
  text-align: center;
}
</style>
<script>
import { apiFetch } from '@/api.js';

export default {
  data() {
    return {
      id: null,
      user: "",
      role: ""
    }
  },
  methods: {
    async getUser() {
      const response = await apiFetch('/example/me')
      const data = await response.json()
      this.id = data.data.id
      this.user = data.data.username
      this.role = data.data.role
    }
  },
  async mounted() {
    await this.getUser()
    console.log("==")
    console.log(this.id, this.user, this.role)
  }
}
</script>