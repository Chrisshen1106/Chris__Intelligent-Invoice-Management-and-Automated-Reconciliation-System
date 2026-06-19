<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">{{ $t('admin.admin_user_management') }}</p>
        <h1>{{ $t('admin.admin_title') }}</h1>
        <p>{{ $t('admin.admin_description') }}</p>
      </div>
    </header>

    <section class="action-panel">
      <div class="panel-heading">
        <div>
          <h2>{{ $t('admin.admin_system_controls') }}</h2>
          <p>{{ $t('admin.admin_controls_description') }}</p>
        </div>
      </div>

      <div class="action-grid">
        <button class="admin-action-card" @click="openCreateUserModal">
          <span class="action-icon">＋</span>
          <span>
            <strong>{{ $t('admin.admin_createUser') }}</strong>
            <small>{{ $t('admin.admin_createUser_hint') }}</small>
          </span>
        </button>
        <button class="admin-action-card" @click="openChangePermissionsModal">
          <span class="action-icon">↻</span>
          <span>
            <strong>{{ $t('admin.admin_changePermissions') }}</strong>
            <small>{{ $t('admin.admin_changePermissions_hint') }}</small>
          </span>
        </button>
      </div>
    </section>

    <section class="settings-panel">
      <div class="panel-heading">
        <div>
          <h2>{{ $t('admin.settings_title') }}</h2>
          <p>{{ $t('admin.settings_description') }}</p>
        </div>
        <button class="secondary-btn sm" @click="fetchSystemSettings" :disabled="settingsLoading">
          {{ settingsLoading ? $t('admin.settings_loading') : $t('admin.settings_reload') }}
        </button>
      </div>

      <div v-if="settingsLoading" class="settings-loading">
        <span class="spinner"></span> {{ $t('admin.settings_loading') }}
      </div>

      <div v-else-if="settingsError" class="settings-error">
        {{ settingsError }}
      </div>

      <div v-else-if="systemSettings.length === 0" class="empty-box">
        {{ $t('admin.settings_empty') }}
      </div>

      <div v-else class="settings-list">
        <div
          v-for="setting in systemSettings"
          :key="setting.key"
          class="setting-card"
        >
          <div class="setting-info">
            <div class="setting-title-row">
              <div class="setting-key">{{ setting.key }}</div>
              <span class="setting-type">{{ settingTypeLabel(setting) }}</span>
            </div>
            <div class="setting-description">{{ settingDescription(setting) }}</div>
          </div>
          <div class="setting-control">
            <template v-if="editingKey === setting.key">
              <input
                v-model="editingValue"
                class="setting-input"
                :type="setting.type === 'number' ? 'number' : 'text'"
                :step="setting.type === 'number' ? 'any' : undefined"
                @keyup.enter="saveSettingValue(setting)"
                @keyup.escape="cancelEdit"
              />
              <div class="setting-actions">
                <button class="btn-save" @click="saveSettingValue(setting)">{{ $t('admin.settings_save') }}</button>
                <button class="btn-cancel" @click="cancelEdit">{{ $t('admin.settings_cancel') }}</button>
              </div>
            </template>
            <template v-else>
              <span class="setting-value">{{ formatSettingDisplay(setting) }}</span>
              <button class="btn-edit" @click="startEdit(setting)">{{ $t('admin.settings_edit') }}</button>
            </template>
          </div>
          <div v-if="settingSaveSuccess === setting.key" class="setting-toast">
            {{ $t('admin.settings_saved') }}
          </div>
        </div>
      </div>
    </section>

    <CreateUserModal v-if="showCreateUserModal" @close="closeCreateUserModal" />
    <ChangePermissionsModal v-if="showChangePermissionsModal" @close="closeChangePermissionsModal" />
  </div>
</template>

<script>
import CreateUserModal from '@/components/CreateUserModal.vue';
import ChangePermissionsModal from '@/components/ChangePermissionsModal.vue';
import { apiFetch } from '@/api.js';
// 實際上線時 apiFetch 是對的，底下supabase只是方便測試，實際應該拿掉底下的supabase
import { supabase } from '../../supabase.js';

export default {
  name: 'Admin',
  components: {
    CreateUserModal,
    ChangePermissionsModal,
  },
  data() {
    return {
      showCreateUserModal: false,
      showChangePermissionsModal: false,
      // System Settings
      systemSettings: [],
      settingsLoading: false,
      settingsError: null,
      editingKey: null,
      editingValue: null,
      settingSaveSuccess: null,
    };
  },
  created() {
    this.fetchSystemSettings();
  },
  methods: {
    openCreateUserModal() {
      this.showCreateUserModal = true;
    },
    closeCreateUserModal() {
      this.showCreateUserModal = false;
    },
    openChangePermissionsModal() {
      this.showChangePermissionsModal = true;
    },
    closeChangePermissionsModal() {
      this.showChangePermissionsModal = false;
    },

    // ── System Settings ──
    async fetchSystemSettings() {
      this.settingsLoading = true;
      this.settingsError = null;
      try {
        // const res = await apiFetch('/admin/system-settings');
        // if (!res.ok) throw new Error(`HTTP ${res.status}`);
        // this.systemSettings = await res.json();

        // 開發時透過前端接DB，實際上線使用上方註解部分，底下的程式碼可以移除
        const { data,error } = await supabase.rpc('get_system_settings', {})
        if (error) throw error
        this.systemSettings = (data || [])
          .filter(u => u.type !== null && typeof u.value !== 'object')
          .map(u => ({
            key: u.key,
            value: u.value,
            type: u.type,
            description_en: u.description_en,
            description_zh: u.description_zh,
          }))
        console.log(this.systemSettings)
      } catch (e) {
        this.settingsError = `Failed to load settings: ${e.message}`;
      } finally {
        this.settingsLoading = false;
      }
    },

    settingDescription(setting) {
      const locale = this.$i18n.locale;
      if (locale === 'zh-TW' || locale.startsWith('zh')) {
        return setting.description_zh || setting.description_en || '';
      }
      return setting.description_en || setting.description_zh || '';
    },

    formatSettingDisplay(setting) {
      if (setting.type === 'number') {
        // Show percentages in a friendlier format when value is < 1
        if (this.isPercentSetting(setting)) {
          return `${(setting.value * 100).toFixed(2)}%`;
        }
        return setting.value;
      }
      if (setting.type === 'boolean') {
        return setting.value ? '✓' : '✗';
      }
      return setting.value;
    },

    settingTypeLabel(setting) {
      if (this.isPercentSetting(setting)) return '%';
      return setting.type || 'value';
    },

    isPercentSetting(setting) {
      return setting.type === 'number' && (setting.key.includes('rate') || setting.key.includes('ratio'));
    },

    startEdit(setting) {
      this.editingKey = setting.key;
      this.editingValue = this.isPercentSetting(setting)
        ? Number(setting.value) * 100
        : setting.value;
      this.settingSaveSuccess = null;
    },

    cancelEdit() {
      this.editingKey = null;
      this.editingValue = null;
    },

    async saveSettingValue(setting) {
      let newValue = this.editingValue;
      if (setting.type === 'number') {
        newValue = Number(newValue);
        if (isNaN(newValue)) return;
        if (this.isPercentSetting(setting)) {
          newValue = newValue / 100;
        }
      }
      try {
        // const res = await apiFetch(`/admin/system-settings/${setting.key}`, {
        //   method: 'PUT',
        //   headers: { 'Content-Type': 'application/json' },
        //   body: JSON.stringify({ value: newValue }),
        // });
        // if (!res.ok) throw new Error(`HTTP ${res.status}`);
        // // Update local state
        // setting.value = newValue;
        // this.editingKey = null;
        // this.editingValue = null;
        // this.settingSaveSuccess = setting.key;
        // setTimeout(() => {
        //   if (this.settingSaveSuccess === setting.key) {
        //     this.settingSaveSuccess = null;
        //   }
        // }, 2000);
        // 實際上線時可以移除底下程式碼
        const { error } = await supabase.rpc('update_system_setting', {
          p_key: setting.key,
          p_value: newValue,
        })
        if (error) throw error
        // 更新本地狀態
        setting.value = newValue;
        this.editingKey = null;
        this.editingValue = null;
        this.settingSaveSuccess = setting.key;
        setTimeout(() => {
          if (this.settingSaveSuccess === setting.key) {
            this.settingSaveSuccess = null;
          }
        }, 2000);
      } catch (e) {
        alert(`Save failed: ${e.message}`);
      }
    },
  },
};
</script>

<style scoped>
.admin-page {
  min-height: calc(100vh - 57px);
  padding: 1.5rem;
  background: #f8fafc;
  color: #0f172a;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 1.5rem;
  align-items: flex-start;
  max-width: 1180px;
  margin: 0 auto 1rem;
  padding: 1.25rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.eyebrow {
  margin: 0 0 0.45rem;
  color: #0891b2;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.page-header h1 {
  margin: 0;
  color: #0f172a;
  font-size: 1.7rem;
  line-height: 1.2;
  letter-spacing: 0;
}

.page-header p {
  margin: 0.55rem 0 0;
  max-width: 680px;
  color: #64748b;
  line-height: 1.55;
}

.setting-actions {
  display: flex;
  gap: 0.55rem;
  align-items: center;
  flex-wrap: wrap;
}

.primary-btn,
.secondary-btn,
.btn-edit,
.btn-save,
.btn-cancel {
  min-height: 36px;
  padding: 0.55rem 0.85rem;
  border: 1px solid transparent;
  border-radius: 7px;
  font-size: 0.86rem;
  font-weight: 800;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s, opacity 0.15s;
}

.primary-btn {
  background: #0891b2;
  color: #fff;
  box-shadow: 0 10px 20px rgba(8, 145, 178, 0.18);
}

.primary-btn:hover {
  background: #0e7490;
}

.secondary-btn,
.btn-edit {
  border-color: #cbd5e1;
  background: #fff;
  color: #334155;
}

.secondary-btn:hover,
.btn-edit:hover {
  border-color: #94a3b8;
  background: #f8fafc;
}

.secondary-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.secondary-btn.sm {
  min-height: 32px;
  padding: 0.42rem 0.7rem;
  font-size: 0.8rem;
}

.action-panel,
.settings-panel {
  max-width: 1180px;
  margin-right: auto;
  margin-left: auto;
}

.action-panel,
.settings-panel {
  margin-bottom: 1rem;
  padding: 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.panel-heading {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  margin-bottom: 0.95rem;
}

.panel-heading h2 {
  margin: 0;
  color: #0f172a;
  font-size: 1.08rem;
  letter-spacing: 0;
}

.panel-heading p {
  margin: 0.35rem 0 0;
  color: #64748b;
  font-size: 0.9rem;
  line-height: 1.5;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}

.admin-action-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 0.8rem;
  align-items: center;
  width: 100%;
  padding: 0.95rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  color: #0f172a;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s, border-color 0.15s, transform 0.15s;
}

.admin-action-card:hover {
  border-color: #7dd3fc;
  background: #f0f9ff;
  transform: translateY(-1px);
}

.action-icon {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  width: 42px;
  height: 42px;
  border-radius: 8px;
  background: #0891b2;
  color: #fff;
  font-size: 1.05rem;
  font-weight: 900;
}

.admin-action-card strong,
.admin-action-card small {
  display: block;
}

.admin-action-card strong {
  font-size: 0.96rem;
}

.admin-action-card small {
  margin-top: 0.2rem;
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.45;
}

.settings-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  color: #64748b;
  font-size: 0.9rem;
}

.spinner {
  display: inline-block;
  width: 18px;
  height: 18px;
  border: 2px solid #e2e8f0;
  border-top-color: #0891b2;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.settings-error {
  padding: 1rem;
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fef2f2;
  color: #991b1b;
  font-size: 0.9rem;
}

.empty-box {
  padding: 1.5rem;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  color: #64748b;
  text-align: center;
}

.settings-list {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.setting-card {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 1rem;
  padding: 0.95rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  transition: background 0.15s, border-color 0.15s;
}

.setting-card:hover {
  border-color: #cbd5e1;
  background: #fbfdff;
}

.setting-info {
  min-width: 0;
}

.setting-title-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 0.25rem;
}

.setting-key {
  overflow-wrap: anywhere;
  color: #0f172a;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
  font-size: 0.9rem;
  font-weight: 800;
}

.setting-type {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 0.5rem;
  border: 1px solid #e0f2fe;
  border-radius: 999px;
  background: #f0f9ff;
  color: #0369a1;
  font-size: 0.72rem;
  font-weight: 900;
  text-transform: uppercase;
}

.setting-description {
  color: #64748b;
  font-size: 0.84rem;
  line-height: 1.45;
}

.setting-control {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  justify-content: flex-end;
}

.setting-value {
  max-width: 260px;
  min-width: 64px;
  padding: 0.35rem 0.65rem;
  overflow: hidden;
  border: 1px solid #bae6fd;
  border-radius: 7px;
  background: #f0f9ff;
  color: #0369a1;
  font-size: 0.9rem;
  font-weight: 800;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.setting-input {
  width: 140px;
  padding: 0.52rem 0.65rem;
  border: 1px solid #0891b2;
  border-radius: 7px;
  font-size: 0.9rem;
  outline: none;
  text-align: center;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.setting-input:focus {
  border-color: #0e7490;
  box-shadow: 0 0 0 3px rgba(8, 145, 178, 0.15);
}

.btn-save {
  background: #059669;
  color: #fff;
}

.btn-save:hover {
  background: #047857;
}

.btn-cancel {
  border-color: #fecaca;
  background: #fff;
  color: #b91c1c;
}

.btn-cancel:hover {
  background: #fef2f2;
}

.setting-toast {
  position: absolute;
  right: 1rem;
  top: -10px;
  padding: 0.25rem 0.6rem;
  border: 1px solid #bbf7d0;
  border-radius: 999px;
  background: #f0fdf4;
  color: #047857;
  font-size: 0.76rem;
  font-weight: 800;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

@media (max-width: 900px) {
  .admin-page {
    padding: 1rem;
  }

  .page-header,
  .panel-heading {
    flex-direction: column;
  }

  .action-grid {
    grid-template-columns: 1fr;
  }

  .setting-card {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .setting-control {
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .setting-value {
    max-width: 100%;
  }
}

@media (max-width: 520px) {
  .setting-actions,
  .setting-control {
    flex-direction: column;
    align-items: stretch;
  }

  .primary-btn,
  .secondary-btn,
  .btn-edit,
  .btn-save,
  .btn-cancel,
  .setting-input {
    width: 100%;
  }
}
</style>
