const moduleExampleRoutes = [
  {
    path: '/module_example',
    name: 'module_example',
    component: () => import('../views/module_example/Index.vue')
  },

]

export default moduleExampleRoutes
