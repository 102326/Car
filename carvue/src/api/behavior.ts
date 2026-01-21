import axios from 'axios'
// 引入类型定义 (根据 types/index.ts)
import type { ICarProduct } from '@/types'

// 创建局部 axios 实例，走 Vite Proxy (/api)
const request = axios.create({
    baseURL: '/api/v1',
    timeout: 5000
})

// 拦截器：自动注入 Token
request.interceptors.request.use((config) => {
    const token = localStorage.getItem('token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

/**
 * 1. 添加浏览历史
 * 后端返回: { "msg": "ok" }
 */
export const addHistory = (carId: number | string) => {
    return request.post<{ msg: string }>(`/user/history/${carId}`)
}

/**
 * 2. 获取浏览历史列表
 * 后端返回: [ {id: 1, name: ...}, ... ] (直接数组)
 */
export const getHistory = () => {
    return request.get<ICarProduct[]>('/user/history')
}

/**
 * 3. 切换收藏状态
 * 后端返回: { "is_favorite": boolean }
 */
export const toggleFavorite = (carId: number | string) => {
    return request.post<{ is_favorite: boolean }>(`/user/favorite/${carId}`)
}

/**
 * 4. 检查是否已收藏
 * 后端返回: { "is_favorite": boolean }
 */
export const checkFavorite = (carId: number | string) => {
    return request.get<{ is_favorite: boolean }>(`/user/favorite/check/${carId}`)
}

/**
 * 5. 获取收藏列表
 * 后端返回: [ {id: 1, name: ...}, ... ] (直接数组)
 */
export const getFavorites = () => {
    return request.get<ICarProduct[]>('/user/favorite')
}