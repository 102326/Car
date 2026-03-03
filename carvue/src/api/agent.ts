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

/**
 * 【新增】发送消息给 Agent 并接收流式回复 (Streaming)
 * @param data 聊天请求数据
 * @param onChunk 每次收到数据块时的回调函数
 */
export const sendAgentMessageStream = async (
    data: AgentChatRequest,
    onChunk: (text: string) => void
): Promise<void> => {
    // 1. 手动获取 token 组装 Header
    const token = localStorage.getItem('token')
    const headers: Record<string, string> = {
        'Content-Type': 'application/json'
    }
    if (token) {
        headers['Authorization'] = `Bearer ${token}`
    }

    // 2. 使用原生 fetch 发起请求，以便获取 ReadableStream
    const response = await fetch('/api/v1/agent/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify(data)
    })

    // 3. 处理鉴权和错误
    if (!response.ok) {
        if (response.status === 401) {
            throw new Error('401') // 抛出特定错误让组件去跳登录
        }
        throw new Error(`HTTP Error: ${response.status}`)
    }

// 4. 解析数据流
    const reader = response.body?.getReader()
    const decoder = new TextDecoder('utf-8')
    if (!reader) return

    let buffer = '' // 用来拼接可能被截断的数据块

    while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        
        // SSE 格式中，每个数据块以连续两个换行符 \n\n 结束
        const messages = buffer.split('\n\n')
        
        // 最后一个元素可能是未接收完整的块，留在 buffer 里等下次循环
        buffer = messages.pop() || ''

        for (const message of messages) {
            // 只处理以 data: 开头的消息
            if (message.startsWith('data: ')) {
                const chunkData = message.substring(6) // 去掉 'data: ' 前缀
                
                // 处理流结束信号
                if (chunkData.trim() === '[DONE]') {
                    return 
                }
                
                // 将转义的换行符还原，并推给 UI 组件
                const parsedText = chunkData.replace(/\\n/g, '\n')
                onChunk(parsedText)
            }
        }
    }
}