<script setup lang="ts">
import { ref, nextTick, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import MarkdownIt from 'markdown-it'

const router = useRouter()
const md = new MarkdownIt()

// --- 状态定义 ---
const isOpen = ref(false)         // 窗口开关
const isTyping = ref(false)       // 是否正在生成
const inputText = ref('')         // 输入框内容
const messages = ref<any[]>([])   // 消息列表
const socket = ref<WebSocket | null>(null)
const chatBodyRef = ref<HTMLElement | null>(null)

// 消息结构类型
interface IChatMessage {
  role: 'user' | 'ai'
  content: string       // 文本内容 (Markdown)
  cars?: any[]          // 关联车辆数据
  isError?: boolean
}

// --- 核心逻辑: WebSocket 连接 ---
const connectWebSocket = () => {
  const token = localStorage.getItem('token')
  if (!token) {
    showToast('请先登录')
    router.push('/login')
    return
  }

  // 避免重复连接
  if (socket.value && socket.value.readyState === WebSocket.OPEN) return

  // 初始化 WS
  // 注意：这里假设后端端口是 8000，如果是 8888 请自行调整
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const wsUrl = `${protocol}://localhost:8000/api/v1/chat/ws?token=${token}`

  socket.value = new WebSocket(wsUrl)

  socket.value.onopen = () => {
    console.log('AI Agent Connected')
  }

  socket.value.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data)
      handleSocketEvent(payload)
    } catch (e) {
      console.error('WS Parse Error', e)
    }
  }

  socket.value.onclose = (e) => {
    console.log('AI Agent Disconnected', e.code)
    isTyping.value = false
    if (e.code === 1008) {
      showToast('登录过期，请重新登录')
      localStorage.removeItem('token')
    }
  }

  socket.value.onerror = (e) => {
    console.error('WS Error', e)
    isTyping.value = false
  }
}

// --- 核心逻辑: 事件分发 (Event Driven) ---
const handleSocketEvent = (payload: any) => {
  const lastMsg = messages.value[messages.value.length - 1]

  switch (payload.type) {
      // 1. 收到相关车辆数据 -> 插入到当前 AI 消息中
    case 'related_cars':
      if (lastMsg && lastMsg.role === 'ai') {
        lastMsg.cars = payload.data
      } else {
        // 如果还没有 AI 消息，先创建一个
        messages.value.push({ role: 'ai', content: '', cars: payload.data })
      }
      scrollToBottom()
      break

      // 2. 收到文本流 -> 追加到当前 AI 消息
    case 'stream_text':
      isTyping.value = true
      if (lastMsg && lastMsg.role === 'ai') {
        lastMsg.content += payload.content
      } else {
        messages.value.push({ role: 'ai', content: payload.content })
      }
      scrollToBottom()
      break

      // 3. 结束信号
    case 'done':
      isTyping.value = false
      break

      // 4. 错误信号
    case 'error':
      isTyping.value = false
      messages.value.push({ role: 'ai', content: payload.message, isError: true })
      scrollToBottom()
      break
  }
}

// --- 交互逻辑 ---
const toggleWindow = () => {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    connectWebSocket()
    // 如果是第一次打开且没消息，加个欢迎语
    if (messages.value.length === 0) {
      messages.value.push({
        role: 'ai',
        content: '你好！我是 Jarvis，你的智能选车顾问。\n告诉我你的预算、用途或偏好，我来帮你找车！'
      })
    }
    nextTick(scrollToBottom)
  }
}

const sendMessage = () => {
  const text = inputText.value.trim()
  if (!text || !socket.value || socket.value.readyState !== WebSocket.OPEN) return

  // 1. 上屏用户消息
  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  scrollToBottom()

  // 2. 发送给后端
  socket.value.send(text)

  // 3. 预置一个空的 AI 消息等待回流 (优化体验)
  isTyping.value = true
  messages.value.push({ role: 'ai', content: '' })
}

const scrollToBottom = () => {
  if (chatBodyRef.value) {
    chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight
  }
}

// 点击车辆卡片
const goDetail = (carId: number) => {
  isOpen.value = false // 关闭聊天窗
  router.push(`/car/${carId}`)
}

// 组件销毁时断开连接
onUnmounted(() => {
  if (socket.value) socket.value.close()
})

// 监听 Markdown 渲染，防止 XSS (markdown-it 默认转义 html)
const renderMD = (text: string) => {
  return md.render(text || '')
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
            <span v-if="isTyping" class="typing-dot">...</span>
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
                <span v-if="isTyping && index === messages.length - 1 && msg.role === 'ai'" class="cursor">|</span>
              </div>
            </div>

            <div class="msg-avatar user-avatar" v-if="msg.role === 'user'">ME</div>
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
          <button @click="sendMessage" :disabled="!inputText || isTyping">发送</button>
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
.typing-dot { animation: blink 1s infinite; }

.chat-body { flex: 1; overflow-y: auto; padding: 16px; }

.message-row { display: flex; margin-bottom: 20px; gap: 10px; }
.message-row.user { flex-direction: row-reverse; }

.msg-avatar {
  width: 36px; height: 36px;
  background: #fff; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);
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
  /* 适配 iPhone 底部安全区 */
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
}
.chat-footer button:disabled { opacity: 0.5; }

.mask {
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.4);
  z-index: 1000;
}

/* 动画 */
.slide-up-enter-active, .slide-up-leave-active { transition: transform 0.3s ease; }
.slide-up-enter-from, .slide-up-leave-to { transform: translateY(100%); }
.cursor { animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: 0; } }
</style>