<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-box">
      <div class="modal-header">
        <h2>{{ $t('admin.admin_createUser') }}</h2>
        <button class="btn-close" @click="$emit('close')">&#x2715;</button>
      </div>
      <div class="modal-body">
        <table class="modern-table">
          <thead>
            <tr>
              <th>{{ $t('admin.admin_applicationTime') }}</th>
              <th>{{ $t('admin.admin_applicationAccount') }}</th>
              <th>{{ $t('admin.admin_actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td class="text-muted">{{ user.applicationTime }}</td>
              <td class="text-bold">{{ user.applicationAccount }}</td>
              <td>
                <div class="action-row">
                  <select v-model="user.selectedRole" class="role-select">
                    <option disabled value="">{{ $t('admin.admin_selectRole') }}</option>
                    <option value="E">{{ $t('admin.admin_generalEmployee') }}</option>
                    <option value="A">{{ $t('admin.admin_accountant') }}</option>
                    <option value="M">{{ $t('admin.admin_financeManager') }}</option>
                  </select>
                  <button class="btn-approve" @click="approveUser(user)" :disabled="!user.selectedRole">{{ $t('admin.admin_approve') }}</button>
                  <button class="btn-delete" @click="deleteUser(user.id)">{{ $t('admin.admin_delete') }}</button>
                </div>
              </td>
            </tr>
            <tr v-if="users.length === 0">
              <td colspan="3" class="empty-row">—</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { supabase } from '../supabase.js'

export default {
  name: 'CreateUserModal',
  data() {
    return {
      users: []
    };
  },
  async mounted() {
    await this.fetchPendingUsers();
  },
  methods: {
    async fetchPendingUsers() {
      // 使用 admin_get_users RPC 取得所有使用者，再篩選待審核的
      const { data, error } = await supabase.rpc('admin_get_users', {});
      if (error) {
        console.error('Failed to fetch pending users:', error);
        return;
      }
      // admin_get_users 回傳 jsonb[]，篩選 account_status = 'pending' 或 is_active = false 的待審核使用者
      const allUsers = Array.isArray(data) ? data : [];
      this.users = allUsers
        .filter(u => u.accountStatus === 'pending' || u.account_status === 'pending' || u.is_active === false)
        .map(u => ({
          id: u.userId || u.user_id || u.id,
          applicationTime: (u.applyTime)
            ? new Date(u.applyTime).toLocaleString()
            : '-',
          applicationAccount: u.email || u.fullName || u.full_name || u.id,
          selectedRole: 'E'
        }));
    },
    async approveUser(user) {
      if (!user.selectedRole) return;

      // 使用建議的 admin_approve_or_reject_user RPC (p_action_type=1 核准)
      const { data, error } = await supabase.rpc('admin_approve_or_reject_user', {
        p_user_id: user.id,
        p_action_type: 1,
        p_assigned_role: user.selectedRole
      });

      if (error) {
        console.error('Failed to approve user:', error);
        alert(error.message);
        return;
      }
      console.log('User approved:', data);
      this.users = this.users.filter(u => u.id !== user.id);
    },
    async deleteUser(id) {
      // 使用 admin_approve_or_reject_user RPC (p_action_type=2 拒絕/停用)
      // 不能直接 .delete() profiles 表，RLS 會阻擋
      const { data, error } = await supabase.rpc('admin_approve_or_reject_user', {
        p_user_id: id,
        p_action_type: 2
      });

      if (error) {
        console.error('Failed to reject user:', error);
        alert(error.message);
        return;
      }
      console.log('User rejected:', data);
      this.users = this.users.filter(user => user.id !== id);
    }
  }
};
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15,23,42,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}
.modal-box {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.18);
  width: 100%;
  max-width: 640px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.3rem 1.6rem;
  border-bottom: 1px solid #f1f5f9;
}
.modal-header h2 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: #1e293b;
}
.btn-close {
  background: none;
  border: none;
  font-size: 1rem;
  color: #94a3b8;
  cursor: pointer;
  padding: 0.3rem 0.5rem;
  border-radius: 6px;
  transition: background 0.2s;
}
.btn-close:hover { background: #f1f5f9; color: #475569; }
.modal-body {
  padding: 1.2rem 1.6rem;
  overflow-y: auto;
  flex: 1;
}
.modern-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.9rem;
}
.modern-table th {
  padding: 0.75rem 0.9rem;
  color: #94a3b8;
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 2px solid #f1f5f9;
  white-space: nowrap;
}
.modern-table td {
  padding: 0.85rem 0.9rem;
  border-bottom: 1px solid #f8fafc;
  color: #475569;
  vertical-align: middle;
}
.modern-table tbody tr:hover td { background: #f8fafc; }
.text-bold { font-weight: 700; color: #1e293b; }
.text-muted { color: #94a3b8; font-size: 0.85rem; }
.empty-row { text-align: center; color: #cbd5e1; padding: 2rem !important; }
.action-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}
.role-select {
  padding: 0.35rem 0.6rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 7px;
  font-size: 0.85rem;
  color: #475569;
  background: #fff;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
}
.role-select:focus { border-color: #6366f1; }
.btn-approve {
  padding: 0.32rem 0.85rem;
  background: #6366f1;
  color: #fff;
  border: none;
  border-radius: 7px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}
.btn-approve:hover:not(:disabled) { background: #4f46e5; }
.btn-approve:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-delete {
  padding: 0.32rem 0.75rem;
  background: #fff;
  color: #ef4444;
  border: 1.5px solid #fecaca;
  border-radius: 7px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
  white-space: nowrap;
}
.btn-delete:hover { background: #fee2e2; border-color: #ef4444; }
</style>


<style scoped>
.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 20px;
  border-radius: 8px;
  width: 80%;
  max-width: 600px;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 20px;
}

table th, table td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

table th {
  background-color: #f4f4f4;
}

select {
  margin-right: 10px;
}

button {
  padding: 8px 12px;
  margin: 0 4px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background-color: #0056b3;
}
</style>