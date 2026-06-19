import { createRouter, createWebHistory } from 'vue-router'
import moduleExampleRoutes from './module_example'
import { supabase } from '../supabase.js'

const disableAccessManagement = import.meta.env.VITE_DISABLE_ACCESS_MANAGEMENT === 'true'

// role_code -> route
const roleRouteMap = {
  E: '/employee-dashboard',
  A: '/finance',
  M: '/finance-manager',
  AD: '/admin'
}

// Default landing for authenticated users when access management is disabled
// or when the role cannot be resolved.
const DEFAULT_AUTHENTICATED_ROUTE = '/employee-dashboard'

// Resolve the best route for an authenticated user.
// Always tries to honour the user's profile.role_code so each role lands on
// their own page. Falls back to DEFAULT_AUTHENTICATED_ROUTE only when the
// profile is missing/invalid (e.g. dev accounts without a profiles row).
async function resolveAuthenticatedRoute(session) {
  const { data: profile } = await supabase
    .from('profiles')
    .select('role_code, is_active')
    .eq('id', session.user.id)
    .maybeSingle()

  // No profile row — only allow fallback in dev mode.
  if (!profile) {
    return disableAccessManagement ? DEFAULT_AUTHENTICATED_ROUTE : null
  }

  // Inactive account — block (return null so caller can send to /login).
  if (!profile.is_active && !disableAccessManagement) {
    return null
  }

  const roleRoute = roleRouteMap[profile.role_code]
  if (roleRoute) return roleRoute

  // role_code not recognised — fallback in dev mode only.
  return disableAccessManagement ? DEFAULT_AUTHENTICATED_ROUTE : null
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Root',
      // Smart entry: redirect to role page if logged in, otherwise /login.
      // Using a component (not just beforeEnter) so the route record matches;
      // the component is never rendered because beforeEnter always redirects.
      component: { render: () => null },
      beforeEnter: async (to, from, next) => {
        const { data: { session } } = await supabase.auth.getSession()
        if (!session) {
          next('/login')
          return
        }
        const target = await resolveAuthenticatedRoute(session)
        next(target || '/login')
      }
    },
    {
      path: '/auth/callback',
      name: 'AuthCallback',
      component: () => import('../views/AuthCallback.vue')
    },
    {
      path: '/auth/pending',
      name: 'PendingApproval',
      component: () => import('../views/auth/PendingApproval.vue')
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/auth/Login.vue')
    },
    {
      path: '/public-api',
      name: 'PublicApi',
      component: () => import('../views/public/PublicApi.vue')
    },
    {
      path: '/public-ocr-demo',
      name: 'PublicOcrDemo',
      component: () => import('../views/public/PublicOcrDemo.vue')
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('../views/auth/Register.vue')
    },
    {
      path: '/employee-dashboard',
      name: 'EmployeeDashboard',
      component: () => import('../views/employee/EmployeeDashboard.vue'),
      meta: { requiresAuth: true, allowedRoles: ['E'] }
    },
    {
      path: '/finance',
      name: 'Finance',
      component: () => import('../views/finance/MatchGroupWorkbench.vue'),
      meta: { requiresAuth: true, allowedRoles: ['A'] }
    },
    {
      path: '/finance-preview',
      name: 'FinancePreview',
      component: () => import('../views/finance/MatchGroupWorkbench.vue')
    },
    {
      path: '/finance-manager',
      name: 'FinanceManager',
      component: () => import('../views/finance_mgr/FinanceManager.vue'),
      meta: { requiresAuth: true, allowedRoles: ['M'] }
    },
    {
      path: '/admin',
      name: 'Admin',
      component: () => import('../views/admin/Admin.vue'),
      meta: { requiresAuth: true, allowedRoles: ['AD'] }
    },
    ...moduleExampleRoutes
  ]
})

router.beforeEach(async (to, from, next) => {
  // Auth pages: if already signed in, send to role page.
  // /auth/pending is excluded so inactive users can stay on it.
  if (to.path === '/login' || to.path === '/register') {
    const { data: { session } } = await supabase.auth.getSession()
    if (session) {
      const target = await resolveAuthenticatedRoute(session)
      if (target) {
        next(target)
        return
      }
    }
    next()
    return
  }

  if (to.meta.requiresAuth) {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) {
      // Authentication is always required for protected routes,
      // regardless of disableAccessManagement (which only skips role checks).
      next({ path: '/login', query: { next: to.fullPath } })
      return
    }

    // Skip role checks when access management is disabled (dev mode).
    if (disableAccessManagement) {
      next()
      return
    }

    // 如果路由有 role 限制，檢查使用者 profile
    if (to.meta.allowedRoles) {
      const { data: profile } = await supabase
        .from('profiles')
        .select('role_code, is_active')
        .eq('id', session.user.id)
        .maybeSingle()

      if (!profile || !profile.is_active || !to.meta.allowedRoles.includes(profile.role_code)) {
        next('/login')
        return
      }
    }
  }
  next()
})

export default router
