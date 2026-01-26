/**
 * 路由配置
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home/index.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/buy',
    name: 'Buy',
    component: () => import('@/views/Buy/index.vue'),
    meta: { title: '买车' }
  },
  {
    path: '/select',
    name: 'Select',
    component: () => import('@/views/Select/index.vue'),
    meta: { title: '选车' }
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
    path: '/search',
    name: 'Search',
    component: () => import('@/views/Search/index.vue'),
    meta: { title: '搜索' }
  },
  {
    path: '/search-result',
    name: 'SearchResult',
    component: () => import('@/views/SearchResult/index.vue'),
    meta: { title: '搜索结果' }
  },
  {
    path: '/subsidy',
    name: 'Subsidy',
    component: () => import('@/views/Subsidy/index.vue'),
    meta: { title: '十亿补贴' }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login/index.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/ai-chat',
    name: 'AIChat',
    component: () => import('@/views/Chat.vue'),
    meta: { title: 'AI 智能客服' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

