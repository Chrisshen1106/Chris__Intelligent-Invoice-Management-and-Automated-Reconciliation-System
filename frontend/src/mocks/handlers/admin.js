import { http, HttpResponse } from 'msw';
import usersGet from './admin/users_get.json';
import usersApprovalPut from './admin/usersApproval_put.json';
import usersPatch from './admin/users_patch.json';
import systemSettingsGet from './admin/systemSettings_get.json';
import systemSettingsPut from './admin/systemSettings_put.json';

const API_BASE = '/api/admin';

export const adminHandlers = [
  http.get(`${API_BASE}/users`, () => {
    return HttpResponse.json(usersGet);
  }),
  http.put(`${API_BASE}/users/:userId/approval`, () => {
    return HttpResponse.json(usersApprovalPut);
  }),
  http.patch(`${API_BASE}/users/:employeeId`, () => {
    return HttpResponse.json(usersPatch);
  }),
  // ── System Settings ──
  http.get(`${API_BASE}/system-settings`, () => {
    return HttpResponse.json(systemSettingsGet);
  }),
  http.put(`${API_BASE}/system-settings/:key`, () => {
    return HttpResponse.json(systemSettingsPut);
  })
];

export default adminHandlers;
