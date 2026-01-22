<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { showToast } from 'vant'

const router = useRouter()
const message = ref('')
const chatList = ref([
  {
    role: 'ai',
    content: '你好！我是 CarFast AI 智能助手，很高兴为你服务。你可以问我关于汽车选购、维护、最新资讯等任何问题。'
  }
])
const loading = ref(false)
const scrollContainer = ref<HTMLElement | null>(null)

const onClickLeft = () => {
  router.back()
}

const scrollToBottom = async () => {
  await nextTick()
  if (scrollContainer.value) {
    scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
  }
}

const onSend = async () => {
  if (!message.value.trim()) return
  if (loading.value) return

  const userMsg = message.value
  chatList.value.push({
    role: 'user',
    content: userMsg
  })
  message.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const response = await axios.post('http://localhost:8000/chat', {
      message: userMsg
    })

    chatList.value.push({
      role: 'ai',
      content: response.data.answer
    })
  } catch (error) {
    console.error('Chat error:', error)
    showToast('服务开小差了，请稍后再试')
    chatList.value.push({
      role: 'ai',
      content: '抱歉，我现在遇到了一点技术问题，请稍后再试。'
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

onMounted(() => {
  scrollToBottom()
})
</script>

<template>
  <div class="chat-container">
    <van-nav-bar
      title="AI 智能客服"
      left-arrow
      fixed
      placeholder
      @click-left="onClickLeft"
    />

    <div class="chat-content" ref="scrollContainer">
      <div
        v-for="(item, index) in chatList"
        :key="index"
        :class="['chat-item', item.role]"
      >
        <div class="avatar">
          <van-icon :name="item.role === 'ai' ? 'service-o' : 'user-o'" />
        </div>
        <div class="message-bubble">
          {{ item.content }}
        </div>
      </div>

      <div v-if="loading" class="chat-item ai">
        <div class="avatar">
          <van-icon name="service-o" />
        </div>
        <div class="message-bubble loading-bubble">
          <van-loading type="spinner" size="20px" />
        </div>
      </div>
    </div>

    <div class="input-area">
      <van-field
        v-model="message"
        placeholder="请输入您的问题..."
        :border="false"
        @keyup.enter="onSend"
      >
        <template #button>
          <van-button
            size="small"
            type="primary"
            @click="onSend"
            :loading="loading"
          >
            发送
          </van-button>
        </template>
      </van-field>
    </div>
  </div>
</template>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #f7f8fa;
}

.chat-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-item {
  display: flex;
  gap: 8px;
  max-width: 85%;
}

.chat-item.user {
  flex-direction: row-reverse;
  align-self: flex-end;
}

.chat-item.ai {
  align-self: flex-start;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  flex-shrink: 0;
}

.chat-item.user .avatar {
  background-color: #e52e2e;
  color: #fff;
}

.chat-item.ai .avatar {
  background-color: #1989fa;
  color: #fff;
}

.message-bubble {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-all;
  white-space: pre-wrap;
}

.chat-item.user .message-bubble {
  background-color: #e52e2e;
  color: #fff;
  border-bottom-right-radius: 2px;
}

.chat-item.ai .message-bubble {
  background-color: #fff;
  color: #323233;
  border-bottom-left-radius: 2px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.loading-bubble {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 50px;
}

.input-area {
  padding: 8px 16px;
  padding-bottom: env(safe-area-inset-bottom);
  background-color: #fff;
  border-top: 1px solid #ebedf0;
}

:deep(.van-field__control) {
  background-color: #f7f8fa;
  padding: 6px 12px;
  border-radius: 18px;
}
</style>
