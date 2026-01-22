<script setup lang="ts">
import { ref } from 'vue'
import type { Ref } from 'vue'

/**
 * 用户信息接口
 */
interface UserInfo {
  nickname: string
  avatar: string
  level: number
  badge: string
  followers: number
  following: number
  coins: number
}

/**
 * 用户信息
 */
const userInfo: Ref<UserInfo> = ref<UserInfo>({
  nickname: '开开心心柚子8402',
  avatar: 'https://via.placeholder.com/80x80/FF6B9D/FFFFFF?text=U',
  level: 1,
  badge: '获取勋章',
  followers: 0,
  following: 0,
  coins: 0
})

/**
 * 是否显示签到提示
 */
const showSignInTip: Ref<boolean> = ref<boolean>(true)

/**
 * 功能菜单接口
 */
interface MenuItem {
  id: number
  icon: string
  name: string
  path?: string
}

/**
 * 主要功能菜单
 */
const mainMenus: MenuItem[] = [
  { id: 1, icon: '✏️', name: '创作中心', path: '/create' },
  { id: 2, icon: '⭐', name: '收藏', path: '/favorite' },
  { id: 3, icon: '⏰', name: '足迹', path: '/history' },
  { id: 4, icon: '📝', name: '订单', path: '/orders' },
  { id: 5, icon: '💬', name: '消息', path: '/messages' }
]

/**
 * 爱车服务菜单
 */
const carServiceMenus: MenuItem[] = [
  { id: 1, icon: '⛽', name: '优惠加油' },
  { id: 2, icon: '🚗', name: '租车' },
  { id: 3, icon: '📊', name: '爱车估值' },
  { id: 4, icon: '💰', name: '我要卖车' },
  { id: 5, icon: '🛍️', name: '易车商城' },
  { id: 6, icon: '🎨', name: '车衣福利' },
  { id: 7, icon: '📱', name: '更多' }
]

/**
 * 其他服务菜单
 */
const otherServiceMenus: MenuItem[] = [
  { id: 1, icon: '🎁', name: '车币福利' },
  { id: 2, icon: '¥', name: '我的车币' },
  { id: 3, icon: '🎫', name: '我的卡券' },
  { id: 4, icon: '📋', name: '点评有礼' },
  { id: 5, icon: '📢', name: '用户反馈' }
]

/**
 * NPS评分弹窗显示状态
 */
const showNPSDialog: Ref<boolean> = ref<boolean>(true)

/**
 * NPS评分值
 */
const npsScore: Ref<number> = ref<number>(-1)

/**
 * 处理扫码
 */
const handleScan = (): void => {
  console.log('扫码')
}

/**
 * 处理安全中心
 */
const handleSecurity = (): void => {
  console.log('安全中心')
}

/**
 * 处理编辑资料
 */
const handleEdit = (): void => {
  console.log('编辑资料')
}

/**
 * 处理签到
 */
const handleSignIn = (): void => {
  console.log('签到')
  showSignInTip.value = false
}

/**
 * 处理主菜单点击
 */
const handleMainMenuClick = (item: MenuItem): void => {
  console.log('点击主菜单:', item.name)
}

/**
 * 处理爱车服务菜单点击
 */
const handleCarServiceClick = (item: MenuItem): void => {
  console.log('点击爱车服务:', item.name)
}

/**
 * 处理其他服务菜单点击
 */
const handleOtherServiceClick = (item: MenuItem): void => {
  console.log('点击其他服务:', item.name)
}

/**
 * 处理添加爱车
 */
const handleAddCar = (): void => {
  console.log('添加爱车')
}

/**
 * 处理NPS评分选择
 */
const handleNPSSelect = (score: number): void => {
  npsScore.value = score
}

/**
 * 提交NPS评分
 */
const handleNPSSubmit = (): void => {
  if (npsScore.value >= 0) {
    console.log('NPS评分:', npsScore.value)
    showNPSDialog.value = false
  }
}

/**
 * 关闭NPS弹窗
 */
const handleNPSClose = (): void => {
  showNPSDialog.value = false
}
</script>

<template>
  <div class="mine-page">
    <!-- 顶部操作栏 -->
    <div class="top-actions">
      <van-icon name="scan" class="action-icon" @click="handleScan" />
      <van-icon name="shield-o" class="action-icon" @click="handleSecurity" />
    </div>

    <!-- 用户信息卡片 -->
    <div class="user-card">
      <div class="user-header">
        <div class="user-avatar">
          <img :src="userInfo.avatar" :alt="userInfo.nickname" />
        </div>
        <div class="user-info">
          <div class="user-name">
            {{ userInfo.nickname }}
            <van-icon name="edit" class="edit-icon" @click="handleEdit" />
          </div>
          <div class="user-badges">
            <div class="level-badge">Lv{{ userInfo.level }}</div>
            <div class="get-badge">{{ userInfo.badge }}</div>
            <div v-if="showSignInTip" class="sign-in-tip" @click="handleSignIn">
              <span>签到+1</span>
            </div>
          </div>
        </div>
      </div>

      <div class="user-stats">
        <div class="stat-item">
          <div class="stat-label">关注</div>
          <div class="stat-value">{{ userInfo.following }}</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <div class="stat-label">粉丝</div>
          <div class="stat-value">{{ userInfo.followers }}</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <div class="stat-label">易车币</div>
          <div class="stat-value">{{ userInfo.coins }}</div>
        </div>
      </div>
    </div>

    <!-- 主要功能菜单 -->
    <div class="main-menus">
      <div 
        v-for="item in mainMenus" 
        :key="item.id"
        class="menu-item"
        @click="handleMainMenuClick(item)"
      >
        <div class="menu-icon">{{ item.icon }}</div>
        <div class="menu-name">{{ item.name }}</div>
      </div>
    </div>

    <!-- 爱车服务 -->
    <div class="service-section">
      <div class="section-header">
        <div class="section-title">爱车服务</div>
        <div class="section-action" @click="handleAddCar">
          <span>添加爱车</span>
          <van-icon name="arrow" />
        </div>
      </div>

      <div class="service-grid">
        <div 
          v-for="item in carServiceMenus" 
          :key="item.id"
          class="service-item"
          @click="handleCarServiceClick(item)"
        >
          <div class="service-icon">{{ item.icon }}</div>
          <div class="service-name">{{ item.name }}</div>
        </div>
      </div>
    </div>

    <!-- 其他服务 -->
    <div class="other-service-section">
      <div class="other-service-grid">
        <div 
          v-for="item in otherServiceMenus" 
          :key="item.id"
          class="other-service-item"
          @click="handleOtherServiceClick(item)"
        >
          <div class="service-icon">{{ item.icon }}</div>
          <div class="service-name">{{ item.name }}</div>
        </div>
      </div>
    </div>

    <!-- NPS评分弹窗 -->
    <van-popup 
      v-model:show="showNPSDialog" 
      round
      closeable
      position="bottom"
      :style="{ padding: '20px' }"
      @click-close-icon="handleNPSClose"
    >
      <div class="nps-dialog">
        <div class="nps-question">是否愿意向朋友推荐易车App?</div>
        
        <div class="nps-scale">
          <div class="scale-label">
            <span>不可能</span>
            <span>极有可能</span>
          </div>
          <div class="scale-numbers">
            <div 
              v-for="score in 11" 
              :key="score - 1"
              :class="['scale-number', { active: npsScore === score - 1 }]"
              @click="handleNPSSelect(score - 1)"
            >
              {{ score - 1 }}
            </div>
          </div>
        </div>

        <div class="nps-submit">
          <van-button 
            type="primary" 
            block 
            round
            :disabled="npsScore < 0"
            @click="handleNPSSubmit"
          >
            提交
          </van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.mine-page {
  width: 100%;
  min-height: 100vh;
  padding-bottom: 50px;
  background: linear-gradient(180deg, #f0f5ff 0%, #f7f8fa 30%);
}

/* 顶部操作栏 */
.top-actions {
  display: flex;
  justify-content: flex-end;
  gap: 20px;
  padding: 12px 16px;
}

.action-icon {
  font-size: 24px;
  color: #323233;
  cursor: pointer;
}

/* 用户信息卡片 */
.user-card {
  margin: 0 16px 16px;
  padding: 20px;
  background-color: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.user-header {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.user-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  overflow: hidden;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-info {
  flex: 1;
}

.user-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 500;
  color: #323233;
  margin-bottom: 8px;
}

.edit-icon {
  font-size: 16px;
  color: #969799;
  cursor: pointer;
}

.user-badges {
  display: flex;
  align-items: center;
  gap: 8px;
}

.level-badge {
  padding: 2px 8px;
  background-color: #e8e8e8;
  border-radius: 10px;
  font-size: 11px;
  color: #646566;
}

.get-badge {
  padding: 2px 8px;
  background-color: #fff3e6;
  border-radius: 10px;
  font-size: 11px;
  color: #ff9500;
}

.sign-in-tip {
  padding: 2px 8px;
  background: linear-gradient(135deg, #ffa500 0%, #ff6b00 100%);
  border-radius: 10px;
  font-size: 11px;
  color: #ffffff;
  cursor: pointer;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

.user-stats {
  display: flex;
  align-items: center;
  justify-content: space-around;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-label {
  font-size: 13px;
  color: #969799;
}

.stat-value {
  font-size: 16px;
  font-weight: 500;
  color: #323233;
}

.stat-divider {
  width: 1px;
  height: 20px;
  background-color: #ebedf0;
}

/* 主要功能菜单 */
.main-menus {
  display: flex;
  justify-content: space-around;
  padding: 20px;
  margin: 0 16px 16px;
  background-color: #ffffff;
  border-radius: 12px;
}

.menu-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.menu-icon {
  font-size: 28px;
}

.menu-name {
  font-size: 12px;
  color: #646566;
}

/* 爱车服务 */
.service-section {
  margin: 0 16px 16px;
  padding: 16px;
  background-color: #ffffff;
  border-radius: 12px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 500;
  color: #323233;
}

.section-action {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #969799;
  cursor: pointer;
}

.service-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.service-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.service-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
  border-radius: 12px;
}

.service-name {
  font-size: 12px;
  color: #646566;
  text-align: center;
}

/* 其他服务 */
.other-service-section {
  margin: 0 16px 16px;
  padding: 16px;
  background-color: #ffffff;
  border-radius: 12px;
}

.other-service-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 20px;
}

.other-service-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

/* NPS评分弹窗 */
.nps-dialog {
  padding: 20px 0;
}

.nps-question {
  font-size: 16px;
  font-weight: 500;
  color: #323233;
  text-align: center;
  margin-bottom: 24px;
}

.nps-scale {
  margin-bottom: 24px;
}

.scale-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 12px;
  color: #969799;
}

.scale-numbers {
  display: flex;
  justify-content: space-between;
  gap: 4px;
}

.scale-number {
  flex: 1;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f7f8fa;
  border-radius: 8px;
  font-size: 14px;
  color: #646566;
  cursor: pointer;
  transition: all 0.3s;
}

.scale-number:hover {
  background-color: #fff1f0;
}

.scale-number.active {
  background-color: #e52e2e;
  color: #ffffff;
  font-weight: bold;
  transform: scale(1.1);
}

.nps-submit :deep(.van-button) {
  background: linear-gradient(135deg, #ff6b6b 0%, #e52e2e 100%);
  border: none;
}

.nps-submit :deep(.van-button--disabled) {
  background: #ebedf0;
}
</style>
