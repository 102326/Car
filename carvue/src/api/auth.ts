import axios from 'axios'
import type { ILoginRequest, ILoginResponse, IUserInfo } from '@/types/auth'

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
 * 后端直接返回 Token: { access_token, token_type, user_name }
 */
export const login = (data: ILoginRequest) => {
    return request.post<ILoginResponse>('/auth/login', data)
}

// 预留：获取钉钉跳转 URL (如果需要后端生成)
export const getDingTalkRedirect = () => {
    return request.get<{ url: string }>('/auth/dingtalk/url')
}

/**
 * 获取当前登录用户信息
 * 后端直接返回 UserInfo: { id, username, nickname, avatar, roles }
 */
export const getUserInfo = () => {
    return request.get<IUserInfo>('/auth/me')
}