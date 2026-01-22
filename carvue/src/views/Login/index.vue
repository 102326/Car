<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast, showLoadingToast } from 'vant'
import { login } from '@/api/auth'
import type { LoginType, ILoginRequest } from '@/types/auth'

const router = useRouter()
const route = useRoute()

// --- 状态管理 ---
const activeTab = ref<LoginType>('sms') // 默认推荐 SMS (登录即注册)
const agree = ref(false)

// 表单数据 (统一管理，实际提交时按需取用)
const form = reactive({
  phone: '',
  code: '',
  username: '',
  password: ''
})

// 倒计时逻辑
const counting = ref(false)
const second = ref(60)
let timer: any = null

// --- 计算属性: 按钮禁用状态 ---
// 根据当前策略判断是否允许提交
const isSubmitDisabled = computed(() => {
  if (!agree.value) return true

  switch (activeTab.value) {
    case 'sms':
      return !/^1[3-9]\d{9}$/.test(form.phone) || form.code.length !== 4
    case 'password':
      return !form.username || !form.password
    case 'dingtalk':
      return false // 钉钉通常点击即跳转
    default:
      return true
  }
})

// --- 核心逻辑: 策略工厂 ---

// 1. 发送验证码 (仅 SMS 策略)
const sendCode = () => {
  if (!/^1[3-9]\d{9}$/.test(form.phone)) {
    showToast('请输入正确的手机号')
    return
  }
  if (counting.value) return

  showLoadingToast({ message: '发送中...', forbidClick: true })

  // 模拟发送 (后续对接后端 /auth/sms/send)
  setTimeout(() => {
    showToast('验证码已发送: 1234')
    counting.value = true
    second.value = 60
    timer = setInterval(() => {
      second.value--
      if (second.value <= 0) {
        clearInterval(timer)
        counting.value = false
      }
    }, 1000)
  }, 1000)
}

// 2. 构造请求 Payload (Factory Pattern)
const createLoginRequest = (): ILoginRequest | null => {
  switch (activeTab.value) {
    case 'sms':
      return {
        login_type: 'sms',
        payload: { phone: form.phone, code: form.code }
      }
    case 'password':
      return {
        login_type: 'password',
        // ✅ 修正: 映射 form.username -> payload.account
        payload: {
          account: form.username,
          password: form.password
        }
      }
    case 'dingtalk':
      return null
    default:
      return null
  }
}

// 3. 执行登录
const handleLogin = async () => {
  // 特殊处理：钉钉登录
  if (activeTab.value === 'dingtalk') {
    handleDingTalkLogin()
    return
  }

  const requestBody = createLoginRequest()
  if (!requestBody) return

  const toast = showLoadingToast({ message: '登录中...', forbidClick: true, duration: 0 })

  try {
    // 调用统一接口
    const res = await login(requestBody)
    toast.close()

    // 假设后端返回标准结构 { code: 200, data: { ... } }
    if (res.data.code === 200 && res.data.data) {
      const { access_token } = res.data.data

      // 存储 Token
      localStorage.setItem('token', access_token)
      showToast({ type: 'success', message: '登录成功' })

      // 跳转
      const redirect = route.query.redirect as string || '/mine'
      router.replace(redirect)
    } else {
      showToast(res.data.msg || '登录失败')
    }
  } catch (error: any) {
    toast.close()
    console.error('Login Error:', error)
    const msg = error.response?.data?.detail || '服务繁忙，请稍后重试'
    showToast(msg)
  }
}

// 4. 钉钉登录处理 (跳转模式)
const handleDingTalkLogin = () => {
  if (!agree.value) {
    showToast('请先勾选协议')
    return
  }
  // 实际项目中，这里应该重定向到钉钉授权 URL
  // const appId = 'YOUR_DINGTALK_APP_ID'
  // const redirectUri = encodeURIComponent('http://your-domain.com/auth/callback')
  // window.location.href = `https://login.dingtalk.com/oauth2/auth?...`

  showToast('正在跳转钉钉授权...')
  setTimeout(() => {
    showToast('模拟：钉钉授权未配置 AppID')
  }, 1000)
}
</script>

<template>
  <div class="login-page">
    <div class="header">
      <van-icon name="cross" size="24" @click="router.back()" />
      <span class="help">遇到问题?</span>
    </div>

    <div class="title-section">
      <h1>CarFast 登录</h1>
      <p>开启您的智能选车之旅</p>
    </div>

    <van-tabs v-model:active="activeTab" shrink :border="false" background="transparent" title-active-color="#333" title-inactive-color="#999" line-width="20px" line-height="3px">
      <van-tab title="验证码登录" name="sms" />
      <van-tab title="密码登录" name="password" />
      <van-tab title="钉钉登录" name="dingtalk" />
    </van-tabs>

    <div class="form-section">

      <div v-if="activeTab === 'sms'" class="strategy-form">
        <div class="input-group">
          <input v-model="form.phone" type="tel" placeholder="请输入手机号" maxlength="11" />
        </div>
        <div class="input-group code-row">
          <input v-model="form.code" type="number" placeholder="请输入验证码" maxlength="4" />
          <span class="send-btn" :class="{ disabled: counting || !/^1[3-9]\d{9}$/.test(form.phone) }" @click="sendCode">
            {{ counting ? `${second}s` : '获取验证码' }}
          </span>
        </div>
        <div class="hint">未注册手机号验证通过后将自动注册</div>
      </div>

      <div v-if="activeTab === 'password'" class="strategy-form">
        <div class="input-group">
          <input v-model="form.username" type="text" placeholder="手机号/用户名" />
        </div>
        <div class="input-group">
          <input v-model="form.password" type="password" placeholder="请输入密码" />
        </div>
        <div class="hint">新用户建议使用验证码登录，自动创建账号</div>
      </div>

      <div v-if="activeTab === 'dingtalk'" class="strategy-form center-mode">
        <div class="dingtalk-box" @click="handleDingTalkLogin">
          <div class="dt-icon">
            <img src="https://img.alicdn.com/tfs/TB1.P.tqQyWBuNjy0FpXXassXXa-1024-1024.png" alt="DingTalk" />
          </div>
          <div class="dt-text">点击进行钉钉授权</div>
        </div>
      </div>

      <button class="submit-btn" :disabled="isSubmitDisabled" @click="handleLogin">
        {{ activeTab === 'dingtalk' ? '前往授权' : '登录 / 注册' }}
      </button>

      <div class="agreement">
        <van-checkbox v-model="agree" icon-size="14px" checked-color="#1989fa">
          我已阅读并同意 <span class="link">《用户协议》</span> 和 <span class="link">《隐私政策》</span>
        </van-checkbox>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  padding: 24px;
  background: #fff;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header { display: flex; justify-content: space-between; margin-bottom: 30px; }
.help { font-size: 14px; color: #666; }

.title-section { margin-bottom: 20px; }
.title-section h1 { font-size: 26px; font-weight: bold; color: #333; margin-bottom: 6px; }
.title-section p { font-size: 14px; color: #999; }

:deep(.van-tabs__nav) { padding-left: 0; }
:deep(.van-tab) { font-size: 16px; font-weight: 500; justify-content: flex-start; margin-right: 20px; flex: none; }

.form-section { flex: 1; margin-top: 20px; }

.strategy-form { animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }

.input-group {
  border-bottom: 1px solid #eee;
  padding: 14px 0;
  margin-bottom: 16px;
}
.input-group input { width: 100%; border: none; font-size: 16px; background: transparent; }
.input-group input:focus { outline: none; }
.input-group input::placeholder { color: #ccc; }

.code-row { display: flex; align-items: center; }
.send-btn { font-size: 14px; color: #1989fa; padding-left: 12px; border-left: 1px solid #eee; cursor: pointer; white-space: nowrap; }
.send-btn.disabled { color: #ccc; pointer-events: none; }

.hint { font-size: 12px; color: #ccc; margin-top: -10px; margin-bottom: 20px; }

.center-mode { display: flex; justify-content: center; padding: 40px 0; }
.dingtalk-box { text-align: center; }
.dt-icon img { width: 64px; height: 64px; border-radius: 12px; margin-bottom: 12px; }
.dt-text { font-size: 14px; color: #666; }

.submit-btn {
  width: 100%; height: 48px;
  background: #1989fa; color: #fff;
  border: none; border-radius: 24px;
  font-size: 16px; font-weight: bold;
  margin-top: 10px;
  transition: opacity 0.3s;
}
.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.agreement { margin-top: 16px; font-size: 12px; color: #999; }
.link { color: #1989fa; }
</style>