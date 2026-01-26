<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { useUserStore } from '@/store/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 表单数据
const phone = ref('')
const code = ref('')
const isAgree = ref(false)

// 倒计时逻辑
const countdown = ref(0)
const isSending = ref(false)

// 按钮状态控制
const isSubmitDisabled = computed(() => {
  return !phone.value || !code.value || !isAgree.value
})

// 发送验证码
const handleSendCode = () => {
  if (!/^1[3-9]\d{9}$/.test(phone.value)) {
    showToast('请输入正确的手机号')
    return
  }

  if (isSending.value) return

  isSending.value = true
  showLoadingToast({ message: '发送中...', forbidClick: true })

  setTimeout(() => {
    closeToast()
    showToast('验证码已发送：1234') // 模拟发送
    code.value = '1234' // 自动填充方便测试
    countdown.value = 60

    const timer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        clearInterval(timer)
        isSending.value = false
      }
    }, 1000)
  }, 500)
}

// 登录处理
const handleLogin = async () => {
  if (!isAgree.value) {
    showToast('请阅读并勾选协议')
    return
  }

  try {
    showLoadingToast({ message: '登录中...', forbidClick: true })
    await userStore.login(phone.value, code.value)

    closeToast()
    showToast({ type: 'success', message: '登录成功' })

    // 登录成功后跳转逻辑
    const redirect = route.query.redirect as string
    if (redirect) {
      router.replace(redirect)
    } else {
      router.replace('/mine') // 默认跳去个人中心
    }
  } catch (error) {
    closeToast()
    showToast('登录失败，请重试')
  }
}

// 返回上一页
const onClickLeft = () => {
  router.back()
}
</script>

<template>
  <div class="login-page">
    <van-nav-bar
        title=""
        left-arrow
        :border="false"
        @click-left="onClickLeft"
        class="login-nav"
    >
      <template #right>
        <span class="nav-text">注册</span>
      </template>
    </van-nav-bar>

    <div class="login-content">
      <div class="header">
        <h1 class="title">欢迎登录易车</h1>
        <p class="subtitle">未注册手机号验证后自动创建账号</p>
      </div>

      <div class="form-area">
        <div class="input-group">
          <van-field
              v-model="phone"
              type="tel"
              placeholder="请输入手机号"
              :border="false"
              clearable
              class="custom-input"
          />
        </div>

        <div class="input-group code-group">
          <van-field
              v-model="code"
              type="digit"
              placeholder="请输入验证码"
              :border="false"
              class="custom-input"
          />
          <span
              class="send-code-btn"
              :class="{ disabled: isSending }"
              @click="handleSendCode"
          >
            {{ countdown > 0 ? `${countdown}s后重发` : '获取验证码' }}
          </span>
        </div>

        <van-button
            round
            block
            type="primary"
            color="#e52e2e"
            class="login-btn"
            :disabled="isSubmitDisabled"
            @click="handleLogin"
        >
          登录
        </van-button>

        <div class="agreement-box">
          <van-checkbox v-model="isAgree" icon-size="14px" checked-color="#e52e2e">
            <span class="agreement-text">
              我已阅读并同意
              <span class="link">《用户协议》</span>
              和
              <span class="link">《隐私政策》</span>
            </span>
          </van-checkbox>
        </div>
      </div>

      <div class="footer-actions">
        <div class="divider">其他登录方式</div>
        <div class="social-icons">
          <div class="icon-item wechat">
            <van-icon name="wechat" />
          </div>
          <div class="icon-item qq">
            <van-icon name="qq" />
          </div>
          <div class="icon-item weibo">
            <van-icon name="weibo" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
}

.login-nav {
  --van-nav-bar-icon-color: #323233;
}

.nav-text {
  font-size: 14px;
  color: #323233;
}

.login-content {
  flex: 1;
  padding: 32px 24px;
}

.header {
  margin-bottom: 40px;
}

.title {
  font-size: 28px;
  color: #323233;
  font-weight: 600;
  margin-bottom: 8px;
}

.subtitle {
  font-size: 14px;
  color: #969799;
}

.form-area {
  margin-bottom: 60px;
}

.input-group {
  margin-bottom: 24px;
  border-bottom: 1px solid #ebedf0;
}

.custom-input {
  padding: 12px 0;
  font-size: 16px;
}

.code-group {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.send-code-btn {
  font-size: 14px;
  color: #e52e2e;
  padding: 8px 0;
  cursor: pointer;
  white-space: nowrap;
}

.send-code-btn.disabled {
  color: #969799;
  cursor: not-allowed;
}

.login-btn {
  margin-top: 40px;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(229, 46, 46, 0.2);
}

.agreement-box {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

.agreement-text {
  font-size: 12px;
  color: #969799;
  line-height: 1.5;
}

.link {
  color: #576b95;
}

.footer-actions {
  margin-top: auto;
}

.divider {
  text-align: center;
  font-size: 12px;
  color: #c8c9cc;
  margin-bottom: 24px;
  position: relative;
}

.divider::before,
.divider::after {
  content: '';
  position: absolute;
  top: 50%;
  width: 30%;
  height: 1px;
  background-color: #ebedf0;
}

.divider::before {
  left: 0;
}

.divider::after {
  right: 0;
}

.social-icons {
  display: flex;
  justify-content: center;
  gap: 32px;
}

.icon-item {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid #ebedf0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #646566;
  transition: all 0.3s;
}

.icon-item:active {
  background-color: #f7f8fa;
}

.wechat { color: #07c160; border-color: #07c160; }
.qq { color: #1989fa; border-color: #1989fa; }
.weibo { color: #e52e2e; border-color: #e52e2e; }
</style>