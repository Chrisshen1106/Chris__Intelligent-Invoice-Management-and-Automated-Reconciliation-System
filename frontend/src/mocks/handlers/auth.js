import { http, HttpResponse } from 'msw';
import googleUrlGet from './auth/googleUrl_get.json';
import googleCallbackPost from './auth/googleCallback_post.json';

const API_BASE = '/api/auth';

export const authHandlers = [
  http.get(`${API_BASE}/google/url`, () => {
    return HttpResponse.json(googleUrlGet);
  }),
  http.post(`${API_BASE}/google/callback`, () => {
    return HttpResponse.json(googleCallbackPost);
  })
];

export default authHandlers;
