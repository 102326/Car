<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import MarkdownIt from 'markdown-it'
import { sendAgentMessage } from '@/api/agent'
import { getUserInfo } from '@/api/auth'
import type { AgentChatResponse } from '@/api/agent'

const router = useRouter()
const md = new MarkdownIt()

// --- 状态定义 ---
const isOpen = ref(false)         // 窗口开关
const isTyping = ref(false)       // 是否正在等待 Agent 响应
const inputText = ref('')         // 输入框内容
const messages = ref<any[]>([])   // 消息列表
const chatBodyRef = ref<HTMLElement | null>(null)
const currentUser = ref<any>(null) // 当前登录用户信息

// 消息结构类型
interface IChatMessage {
  role: 'user' | 'ai'
  content: string       // 文本内容 (Markdown)
  cars?: any[]          // 关联车辆数据
  isError?: boolean
  // Agent 元数据
  steps?: number        // 思考步数
  intent?: string       // 识别意图
  elapsed_ms?: number   // 处理耗时
}

// --- 生命周期 ---
onMounted(async () => {
  // 尝试获取已登录用户信息
  await fetchUserInfo()
})

// --- 获取用户信息 ---
const fetchUserInfo = async () => {
  const token = localStorage.getItem('token')
  if (!token) return
  
  try {
    const res = await getUserInfo()
    // 后端直接返回 UserInfo: { id, username, nickname, avatar, roles }
    if (res.data?.id) {
      currentUser.value = res.data
    }
  } catch (e) {
    console.warn('获取用户信息失败', e)
  }
}

// --- 交互逻辑 ---
const toggleWindow = async () => {
  isOpen.value = !isOpen.value
  
  if (isOpen.value) {
    // 检查登录状态
    const token = localStorage.getItem('token')
    if (!token) {
      showToast('请先登录')
      router.push('/login')
      isOpen.value = false
      return
    }
    
    // 确保有用户信息
    if (!currentUser.value) {
      await fetchUserInfo()
    }
    
    // 首次打开添加欢迎语
    if (messages.value.length === 0) {
      messages.value.push({
        role: 'ai',
        content: '你好！我是 Jarvis，你的智能选车顾问。\n告诉我你的预算、用途或偏好，我来帮你找车！'
      })
    }
    nextTick(scrollToBottom)
  }
}

const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text || isTyping.value) return

  // 1. 上屏用户消息
  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  scrollToBottom()

  // 2. 开始加载状态
  isTyping.value = true

  try {
    // 3. 调用后端 Agent API (带用户ID)
    const response: AgentChatResponse = await sendAgentMessage({
      message: text,
      user_id: currentUser.value?.id
    })

    // 4. 将 Agent 回复追加到消息列表
    messages.value.push({
      role: 'ai',
      content: response.response,
      steps: response.steps,
      intent: response.intent,
      elapsed_ms: response.elapsed_ms
    })

  } catch (error: any) {
    console.error('Agent API Error:', error)
    
    // 处理认证错误
    if (error.response?.status === 401) {
      showToast('登录已过期，请重新登录')
      localStorage.removeItem('token')
      router.push('/login')
      isOpen.value = false
      return
    }
    
    // 显示错误消息
    const errorMsg = error.response?.data?.detail || error.message || '请求失败，请稍后重试'
    messages.value.push({
      role: 'ai',
      content: `抱歉，发生了错误：${errorMsg}`,
      isError: true
    })
    showToast('Agent 请求失败')
  } finally {
    isTyping.value = false
    nextTick(scrollToBottom)
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (chatBodyRef.value) {
      chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight
    }
  })
}

// 点击车辆卡片
const goDetail = (carId: number) => {
  isOpen.value = false
  router.push(`/car/${carId}`)
}

// Markdown 渲染
const renderMD = (text: string) => {
  return md.render(text || '')
}

// 格式化意图显示
const formatIntent = (intent: string | null | undefined): string => {
  const intentMap: Record<string, string> = {
    'search': '🔍 找车',
    'chat': '💬 对话',
    'calculate': '🧮 计算'
  }
  return intent ? (intentMap[intent] || intent) : ''
}
</script>

<template>
  <div class="ai-agent-container">

    <div class="float-ball" :class="{ hidden: isOpen }" @click="toggleWindow">
      <div class="ball-content">
        <span class="icon">🤖</span>
        <span class="text">AI顾问</span>
      </div>
      <div class="ripple"></div>
    </div>

    <transition name="slide-up">
      <div v-if="isOpen" class="chat-window">
        <div class="chat-header">
          <div class="header-left">
            <span class="avatar">🤖</span>
            <span class="title">Jarvis 智能顾问</span>
            <span v-if="isTyping" class="thinking-indicator">
              <span class="thinking-dot"></span>
              <span class="thinking-text">思考中</span>
            </span>
          </div>
          <van-icon name="arrow-down" @click="toggleWindow" />
        </div>

        <div class="chat-body" ref="chatBodyRef">
          <div v-for="(msg, index) in messages" :key="index" class="message-row" :class="msg.role">

            <div class="msg-avatar" v-if="msg.role === 'ai'">🤖</div>

            <div class="msg-content-wrapper">

              <div v-if="msg.cars && msg.cars.length > 0" class="car-cards-container">
                <div class="car-card-scroll">
                  <div v-for="car in msg.cars" :key="car.id" class="mini-car-card" @click="goDetail(car.id)">
                    <img :src="car.image || 'https://img.yzcdn.cn/vant/cat.jpeg'" alt="car" />
                    <div class="car-info">
                      <div class="car-name">{{ car.name }}</div>
                      <div class="car-price">¥{{ car.price }}万</div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="bubble" :class="{ error: msg.isError }">
                <div v-if="msg.role === 'user'">{{ msg.content }}</div>
                <div v-else class="markdown-body" v-html="renderMD(msg.content)"></div>
              </div>

              <!-- Agent 元数据展示 (小字显示在气泡下方) -->
              <div v-if="msg.role === 'ai' && msg.steps !== undefined" class="agent-meta">
                <span v-if="msg.intent" class="meta-item intent">{{ formatIntent(msg.intent) }}</span>
                <span class="meta-item steps">🧠 Steps: {{ msg.steps }}</span>
                <span class="meta-item time">⏱️ {{ msg.elapsed_ms }}ms</span>
              </div>
            </div>

            <div class="msg-avatar user-avatar" v-if="msg.role === 'user'">ME</div>
          </div>

          <!-- Loading 状态显示 -->
          <div v-if="isTyping" class="message-row ai loading-row">
            <div class="msg-avatar">🤖</div>
            <div class="msg-content-wrapper">
              <div class="bubble loading-bubble">
                <div class="loading-animation">
                  <span class="dot"></span>
                  <span class="dot"></span>
                  <span class="dot"></span>
                </div>
                <span class="loading-text">Agent 正在思考...</span>
              </div>
            </div>
          </div>
        </div>

        <div class="chat-footer">
          <input
              v-model="inputText"
              @keyup.enter="sendMessage"
              type="text"
              placeholder="告诉我您的需求，如: 20万的SUV..."
              :disabled="isTyping"
          />
          <button @click="sendMessage" :disabled="!inputText || isTyping">
            <span v-if="isTyping" class="btn-loading">⏳</span>
            <span v-else>发送</span>
          </button>
        </div>
      </div>
    </transition>

    <div v-if="isOpen" class="mask" @click="toggleWindow"></div>
  </div>
</template>

<style scoped>
/* 悬浮球样式 */
.float-ball {
  position: fixed;
  bottom: 80px;
  right: 20px;
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #1989fa, #0570db);
  border-radius: 50%;
  box-shadow: 0 4px 12px rgba(25, 137, 250, 0.4);
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s;
}
.float-ball:active { transform: scale(0.95); }
.float-ball.hidden { transform: scale(0); opacity: 0; }
.ball-content { display: flex; flex-direction: column; align-items: center; color: #fff; font-size: 12px; }
.ball-content .icon { font-size: 24px; margin-bottom: -2px; }

/* 呼吸动画 */
.ripple {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  border-radius: 50%;
  border: 2px solid #1989fa;
  animation: ripple 1.5s infinite;
  opacity: 0;
}
@keyframes ripple {
  0% { transform: scale(1); opacity: 0.6; }
  100% { transform: scale(1.4); opacity: 0; }
}

/* 聊天窗口 */
.chat-window {
  position: fixed;
  bottom: 0; left: 0; width: 100%;
  height: 75vh;
  background: #f7f8fa;
  border-radius: 16px 16px 0 0;
  z-index: 1001;
  display: flex;
  flex-direction: column;
  box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
}

.chat-header {
  padding: 16px;
  background: #fff;
  border-radius: 16px 16px 0 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
}
.header-left { display: flex; align-items: center; gap: 8px; font-weight: bold; font-size: 16px; }

/* 思考中指示器 */
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: 8px;
  color: #1989fa;
  font-weight: normal;
  font-size: 13px;
}
.thinking-dot {
  width: 6px;
  height: 6px;
  background: #1989fa;
  border-radius: 50%;
  animation: pulse 1s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1); }
}

.chat-body { flex: 1; overflow-y: auto; padding: 16px; }

.message-row { display: flex; margin-bottom: 20px; gap: 10px; }
.message-row.user { flex-direction: row-reverse; }

.msg-avatar {
  width: 36px; height: 36px;
  background: #fff; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);
  flex-shrink: 0;
}
.user-avatar { background: #1989fa; color: #fff; font-size: 12px; font-weight: bold; }

.msg-content-wrapper { max-width: 75%; display: flex; flex-direction: column; gap: 8px; }

/* 气泡样式 */
.bubble {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.6;
  word-break: break-word;
  position: relative;
}
.ai .bubble { background: #fff; border-top-left-radius: 2px; color: #333; }
.user .bubble { background: #1989fa; color: #fff; border-top-right-radius: 2px; }
.error { color: #ff4d4f; border: 1px solid #ffccc7; background: #fff2f0 !important; }

/* Loading 气泡 */
.loading-bubble {
  display: flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(135deg, #f0f7ff, #e6f0ff);
  border: 1px dashed #1989fa;
}
.loading-animation {
  display: flex;
  gap: 4px;
}
.loading-animation .dot {
  width: 8px;
  height: 8px;
  background: #1989fa;
  border-radius: 50%;
  animation: bounce 1.4s ease-in-out infinite both;
}
.loading-animation .dot:nth-child(1) { animation-delay: -0.32s; }
.loading-animation .dot:nth-child(2) { animation-delay: -0.16s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}
.loading-text {
  color: #1989fa;
  font-size: 14px;
}

/* Agent 元数据 (小字显示在气泡下方) */
.agent-meta {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: #999;
  padding: 0 4px;
}
.meta-item {
  display: flex;
  align-items: center;
  gap: 2px;
}
.meta-item.intent {
  color: #1989fa;
  font-weight: 500;
}

/* Markdown 样式微调 */
:deep(.markdown-body p) { margin: 0 0 8px 0; }
:deep(.markdown-body p:last-child) { margin: 0; }
:deep(.markdown-body ul) { padding-left: 20px; margin: 4px 0; }
:deep(.markdown-body strong) { color: #1989fa; }

/* 推荐车辆卡片 */
.car-cards-container { width: 100%; overflow-x: auto; margin-bottom: 4px; }
.car-card-scroll { display: flex; gap: 10px; padding-bottom: 4px; }
.mini-car-card {
  flex: 0 0 140px;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  cursor: pointer;
}
.mini-car-card img { width: 100%; height: 90px; object-fit: cover; }
.car-info { padding: 8px; }
.car-name { font-size: 13px; font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.car-price { font-size: 12px; color: #ff4d4f; margin-top: 4px; }

/* 底部输入框 */
.chat-footer {
  padding: 12px 16px;
  background: #fff;
  border-top: 1px solid #eee;
  display: flex;
  gap: 10px;
  padding-bottom: calc(12px + env(safe-area-inset-bottom));
}
.chat-footer input {
  flex: 1;
  background: #f5f6f8;
  border: none;
  border-radius: 20px;
  padding: 10px 16px;
  font-size: 14px;
}
.chat-footer button {
  background: #1989fa; color: #fff;
  border: none; border-radius: 20px;
  padding: 0 20px;
  font-weight: bold;
  min-width: 60px;
}
.chat-footer button:disabled { opacity: 0.5; }
.btn-loading { font-size: 16px; }

.mask {
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.4);
  z-index: 1000;
}

/* 动画 */
.slide-up-enter-active, .slide-up-leave-active { transition: transform 0.3s ease; }
.slide-up-enter-from, .slide-up-leave-to { transform: translateY(100%); }
</style>