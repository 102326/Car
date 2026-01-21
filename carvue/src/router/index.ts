import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home/index.vue'),
    meta: { title: '易车 - 首页' }
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('@/views/Search/index.vue'),
    meta: { title: '搜索入口' }
  },
  {
    path: '/search-result',
    name: 'SearchResult',
    component: () => import('@/views/SearchResult/index.vue'),
    meta: { title: '选车结果' }
  },
  // 详情页 (下一步要做!)
  {
    path: '/car/:id',
    name: 'CarDetail',
    component: () => import('@/views/CarDetail/index.vue'),
    meta: { title: '车辆详情' }
  },
  {
    path: '/buy',
    name: 'Buy',
    component: () => import('@/views/Buy/index.vue'),
    meta: { title: '买新车' }
  },
  {
    path: '/used',
    name: 'Used',
    component: () => import('@/views/Used/index.vue'),
    meta: { title: '二手车' }
  },
  {
    path: '/mine',
    name: 'Mine',
    component: () => import('@/views/Mine/index.vue'),
    meta: { title: '我的' }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login/index.vue'),
    meta: { title: '手机号登录' }
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 简单的路由守卫 (改标题)
router.beforeEach((to, _from, next) => {
  if (to.meta.title) {
    document.title = to.meta.title as string
  }
  next()
})

export default router