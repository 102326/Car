/**
 * Agent API - HTTP 请求模式 (带 Token 认证)
 * 对应后端: carfast/app/api/v1/agent.py
 */

import axios from 'axios'

// 创建带 Token 拦截器的 request 实例
const request = axios.create({
    baseURL: '/api/v1',
    timeout: 60000  // Agent 处理可能较慢，设置 60s 超时
})

// Token 拦截器 (与 auth.ts 保持一致)
request.interceptors.request.use((config) => {
    const token = localStorage.getItem('token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
}, (error) => {
    return Promise.reject(error)
})

// ============================================================================
// Types (与后端 Pydantic 模型严格对应)
// ============================================================================

/** 请求体: 对应后端 ChatRequest */
export interface AgentChatRequest {
    /** 用户消息内容 (1-2000字) */
    message: string
    /** 用户ID（可选，用于会话追踪） */
    user_id?: string | number
}

/** 响应体: 对应后端 ChatResponse */
export interface AgentChatResponse {
    /** Agent 回复内容 */
    response: string
    /** Agent 思考步数 */
    steps: number
    /** 识别到的用户意图 (search/chat/calculate) */
    intent: string | null
    /** 处理耗时（毫秒） */
    elapsed_ms: number
}

// ============================================================================
// API 函数
// ============================================================================

/**
 * 发送消息给 Agent 并获取回复
 * @param data 聊天请求数据
 * @returns Agent 的响应
 */
export const sendAgentMessage = async (data: AgentChatRequest): Promise<AgentChatResponse> => {
    const response = await request.post<AgentChatResponse>('/agent/chat', data)
    return response.data
}
