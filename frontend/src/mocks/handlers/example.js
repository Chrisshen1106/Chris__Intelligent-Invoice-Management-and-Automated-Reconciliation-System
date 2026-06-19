import { http, HttpResponse } from 'msw'

export default [
  http.get('/api/example/me', () => {
    return HttpResponse.json({
      code: 200,
      message: 'Success',
      data: {
        id: 1,
        username: 'mock_user',
        role: 'admin'
      }
    })
  })
]
