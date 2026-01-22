import axios from 'axios'
import type { IApiResponse } from '@/types'
import type { ILoginRequest, ILoginResponse } from '@/types/auth'

const request = axios.create({
    baseURL: '/api/v1',
    timeout: 10000
})

request.interceptors.request.use((config) => {
    const token = localStorage.getItem('token')
    if (token) {
        //以此格式添加：Authorization: Bearer <token>
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
}, (error) => {
    return Promise.reject(error)
})

/**
 * 统一登录接口
 * 支持 password, sms, dingtalk 等多种策略
 */
export const login = (data: ILoginRequest) => {
    // 泛型指定：返回结构是 IApiResponse<ILoginResponse>
    return request.post<IApiResponse<ILoginResponse>>('/auth/login', data)
}

// 预留：获取钉钉跳转 URL (如果需要后端生成)
export const getDingTalkRedirect = () => {
    return request.get<{ url: string }>('/auth/dingtalk/url')
}

export const getUserInfo = () => {
    return request.get<IApiResponse<any>>('/auth/me')
}