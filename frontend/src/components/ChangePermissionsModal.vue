<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-box">
      <div class="modal-header">
        <h2>{{ $t('admin.admin_changePermissions') }}</h2>
        <button class="btn-close" @click="$emit('close')">&#x2715;</button>
      </div>
      <div class="modal-body">
        <table class="modern-table">
          <thead>
            <tr>
              <th>{{ $t('admin.admin_employeeId') }}</th>
              <th>{{ $t('admin.admin_permissionStatus') }}</th>
              <th>{{ $t('admin.admin_actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="employee in employees" :key="employee.id">
              <td class="text-bold">{{ employee.email }}</td>
              <td>
                <span v-if="employee.permission === 'AD'" class="role-text">{{ $t('admin.admin_admin') }}</span>
                <select v-else v-model="employee.permission" class="role-select">
                  <option value="E">{{ $t('admin.admin_generalEmployee') }}</option>
                  <option value="A">{{ $t('admin.admin_accountant') }}</option>
                  <option value="M">{{ $t('admin.admin_financeManager') }}</option>
                </select>
              </td>
              <td>
                <div v-if="employee.permission !== 'AD'" class="action-row">
                  <button class="btn-save" @click="changeRole(employee)" :disabled="employee.permission === employee.originalRole">{{ $t('admin.admin_approve') }}</button>
                  <button class="btn-delete" @click="deleteEmployee(employee.id)">{{ $t('admin.admin_delete') }}</button>
                </div>
              </td>
            </tr>
            <tr v-if="employees.length === 0">
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
  name: 'ChangePermissionsModal',
  data() {
    return {
      employees: []
    };
  },
  async mounted() {
    await this.fetchActiveUsers();
  },
  methods: {
    async fetchActiveUsers() {
      // 使用 admin_get_users RPC 取得所有使用者，再篩選已啟用的
      const { data, error } = await supabase.rpc('admin_get_users', {});
      if (error) {
        console.error('Failed to fetch active users:', error);
        return;
      }
      const allUsers = Array.isArray(data) ? data : [];
      this.employees = allUsers
        .filter(u => (u.accountStatus === 'active' || u.account_status === 'active' || u.is_active === true || u.isActive === true))
        .map(u => ({
          id: u.userId || u.user_id || u.id,
          email: u.email || u.fullName || u.full_name || u.id,
          permission: u.role,
          originalRole: u.role
        }));
    },
    async changeRole(employee) {
      if (employee.permission === employee.originalRole) return;

      // 使用 admin_update_user RPC (p_action_type=1 修改權限)
      const { data, error } = await supabase.rpc('admin_update_user', {
        p_user_id: employee.id,
        p_action_type: 1,
        p_new_role: employee.permission
      });

      if (error) {
        console.error('Failed to change role:', error);
        alert(error.message);
        return;
      }
      console.log('Role changed:', data);
      employee.originalRole = employee.permission;
    },
    async deleteEmployee(id) {
      // 使用 admin_update_user RPC (p_action_type=2 停權帳號)
      // 不能直接 .delete() profiles 表，RLS 會阻擋
      const { data, error } = await supabase.rpc('admin_update_user', {
        p_user_id: id,
        p_action_type: 2
      });

      if (error) {
        console.error('Failed to deactivate user:', error);
        alert(error.message);
        return;
      }
      console.log('User deactivated:', data);
      this.employees = this.employees.filter(e => e.id !== id);
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
  max-width: 560px;
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
.empty-row { text-align: center; color: #cbd5e1; padding: 2rem !important; }
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
  width: 100%;
}
.role-select:focus { border-color: #6366f1; }
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