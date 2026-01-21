<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
// 引入 API 和 类型
import { getHistory, getFavorites } from '@/api/behavior'
// 注意：根据你的 types/index.ts，车型接口叫 ICarProduct
import type { ICarProduct } from '@/types'

const router = useRouter()

// --- 状态管理 ---
const isLogin = ref(false)
const activeTab = ref(0) // 0: 收藏, 1: 足迹
const loading = ref(false)

// 数据列表
const favList = ref<ICarProduct[]>([])
const historyList = ref<ICarProduct[]>([])

// 用户信息 (这里可以扩展为从 /api/v1/auth/me 获取)
const userInfo = ref({
  nickname: '请先登录',
  avatar: '',
  level: 0,
  coins: 0,
  following: 0,
  followers: 0
})

// --- 核心逻辑 ---

onMounted(() => {
  checkLogin()
})

const checkLogin = () => {
  const token = localStorage.getItem('token')
  if (token) {
    isLogin.value = true
    // 模拟已登录用户信息 (进阶：这里应该调用 getUserInfo API)
    userInfo.value = {
      nickname: '尊贵的易车会员',
      avatar: 'https://via.placeholder.com/80x80/1989fa/FFFFFF?text=VIP',
      level: 6,
      coins: 1280,
      following: 12,
      followers: 5
    }
    // 加载行为数据
    loadData()
  }
}

const loadData = async () => {
  loading.value = true
  try {
    // 并行请求：获取收藏 + 获取足迹
    const [resFav, resHist] = await Promise.all([
      getFavorites(),
      getHistory()
    ])

    // 处理收藏数据
    // 注意：根据 behavior.ts 的定义，返回值是 axios response，数据在 data.data 或 data 中
    // 假设后端标准结构是 { code: 200, data: [...] }
    if (resFav.data && Array.isArray(resFav.data)) {
      // 如果后端直接返回列表
      favList.value = resFav.data
    } else if (resFav.data?.data) {
      // 如果后端返回标准 ApiResponse
      favList.value = resFav.data.data
    }

    // 处理足迹数据
    if (resHist.data && Array.isArray(resHist.data)) {
      historyList.value = resHist.data
    } else if (resHist.data?.data) {
      historyList.value = resHist.data.data
    }

  } catch (error) {
    console.error('加载数据失败', error)
    // 如果是 401 未授权，可能会在这里捕获
  } finally {
    loading.value = false
  }
}

// 跳转详情
const goDetail = (id: string | number) => {
  router.push(`/car/${id}`)
}

// 跳转登录
const goLogin = () => {
  if (!isLogin.value) {
    // 这里假设有一个登录页，或者直接用 Auth 组件
    showToast('请先对接登录功能')
    // router.push('/login')
  }
}

// 模拟功能点击
const handleFunction = (name: string) => {
  showToast(`${name} 功能开发中`)
}
</script>

<template>
  <div class="mine-page">
    <div class="user-header-card">
      <div class="top-actions">
        <van-icon name="scan" class="action-icon" @click="handleFunction('扫码')" />
        <van-icon name="setting-o" class="action-icon" @click="handleFunction('设置')" />
      </div>

      <div class="user-info-row" @click="goLogin">
        <div class="avatar-box">
          <img v-if="isLogin" :src="userInfo.avatar" alt="avatar" />
          <div v-else class="avatar-placeholder">
            <van-icon name="user-o" />
          </div>
        </div>
        <div class="text-box">
          <div class="nickname">
            {{ userInfo.nickname }}
            <van-icon v-if="isLogin" name="edit" class="edit-btn" />
          </div>
          <div class="status-tags" v-if="isLogin">
            <span class="tag level">Lv.{{ userInfo.level }}</span>
            <span class="tag vip">年度会员</span>
          </div>
          <div class="login-tip" v-else>点击登录，同步你的爱车数据</div>
        </div>
      </div>

      <div class="stats-row">
        <div class="stat-item">
          <div class="num">{{ userInfo.following }}</div>
          <div class="label">关注</div>
        </div>
        <div class="stat-item">
          <div class="num">{{ userInfo.followers }}</div>
          <div class="label">粉丝</div>
        </div>
        <div class="stat-item">
          <div class="num">{{ userInfo.coins }}</div>
          <div class="label">易车币</div>
        </div>
      </div>
    </div>

    <div class="core-tabs-section">
      <van-tabs v-model:active="activeTab" sticky animated swipeable background="#f7f8fa">

        <van-tab title="我的收藏">
          <div class="car-list" v-if="isLogin">
            <div
                v-for="car in favList"
                :key="car.id"
                class="car-card"
                @click="goDetail(car.id)"
            >
              <div class="img-box">
                <img :src="car.coverImage" />
              </div>
              <div class="info-box">
                <div class="title">{{ car.modelName || car.name }}</div> <div class="tags">
                <van-tag plain type="primary" size="mini">{{ car.seriesName }}</van-tag>
              </div>
                <div class="price-row">
                  <span class="price">¥{{ car.priceRange?.[0] || car.price }}万</span>
                  <van-icon name="arrow" color="#ccc" />
                </div>
              </div>
            </div>
            <van-empty v-if="!favList.length && !loading" description="暂无收藏，快去选车吧" />
            <van-loading v-if="loading" class="loading-state" vertical>加载中...</van-loading>
          </div>
          <div v-else class="not-login-box">
            <van-empty description="登录后查看收藏" />
            <van-button round type="primary" size="small" @click="goLogin">去登录</van-button>
          </div>
        </van-tab>

        <van-tab title="浏览足迹">
          <div class="car-list" v-if="isLogin">
            <div
                v-for="car in historyList"
                :key="car.id"
                class="car-card"
                @click="goDetail(car.id)"
            >
              <div class="img-box">
                <img :src="car.coverImage" />
              </div>
              <div class="info-box">
                <div class="title">{{ car.modelName || car.name }}</div>
                <div class="sub-text">刚刚看过</div>
                <div class="price-row">
                  <span class="price">¥{{ car.priceRange?.[0] || car.price }}万</span>
                </div>
              </div>
            </div>
            <van-empty v-if="!historyList.length && !loading" description="暂无浏览记录" />
            <van-loading v-if="loading" class="loading-state" vertical>加载中...</van-loading>
          </div>
          <div v-else class="not-login-box">
            <van-empty description="登录后查看足迹" />
            <van-button round type="primary" size="small" @click="goLogin">去登录</van-button>
          </div>
        </van-tab>
      </van-tabs>
    </div>

    <div class="service-section">
      <div class="section-title">常用服务</div>
      <van-grid :column-num="4" :border="false">
        <van-grid-item icon="gold-coin-o" text="我的钱包" />
        <van-grid-item icon="records" text="订单中心" />
        <van-grid-item icon="service-o" text="联系客服" />
        <van-grid-item icon="setting-o" text="设置" />
      </van-grid>
    </div>

  </div>
</template>

<style scoped>
.mine-page {
  min-height: 100vh;
  background: #f7f8fa;
  padding-bottom: 50px;
}

/* 头部卡片风格 */
.user-header-card {
  background: linear-gradient(135deg, #e0f2ff 0%, #ffffff 100%);
  padding: 12px 20px 20px;
  margin-bottom: 12px;
}

.top-actions {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
  margin-bottom: 16px;
}
.action-icon {
  font-size: 22px;
  color: #333;
}

.user-info-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.avatar-box {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  overflow: hidden;
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
  background: #fff;
}
.avatar-box img { width: 100%; height: 100%; object-fit: cover; }
.avatar-placeholder {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  font-size: 32px; color: #ccc;
}

.text-box .nickname {
  font-size: 20px;
  font-weight: bold;
  color: #333;
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 6px;
}
.text-box .login-tip { font-size: 14px; color: #666; }

.status-tags { display: flex; gap: 6px; }
.tag { font-size: 10px; padding: 2px 6px; border-radius: 4px; }
.tag.level { background: #333; color: #f0c040; }
.tag.vip { background: #f0c040; color: #fff; }

.stats-row {
  display: flex;
  justify-content: space-around;
}
.stat-item { text-align: center; }
.stat-item .num { font-size: 18px; font-weight: bold; color: #333; }
.stat-item .label { font-size: 12px; color: #999; margin-top: 4px; }

/* 列表区域 */
.core-tabs-section {
  min-height: 300px;
}

.car-list {
  padding: 12px;
}

.car-card {
  background: #fff;
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 10px;
  display: flex;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
}

.img-box {
  width: 100px;
  height: 66px;
  border-radius: 6px;
  overflow: hidden;
  background: #f2f3f5;
}
.img-box img { width: 100%; height: 100%; object-fit: cover; }

.info-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.info-box .title {
  font-size: 15px;
  font-weight: 500;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sub-text { font-size: 12px; color: #999; }

.price-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}
.price-row .price { color: #ff5000; font-weight: bold; font-size: 15px; }

.not-login-box {
  padding: 40px 0;
  text-align: center;
}
.loading-state {
  margin-top: 20px;
  text-align: center;
}

/* 底部服务 */
.service-section {
  background: #fff;
  margin: 12px;
  border-radius: 12px;
  padding: 12px;
}
.section-title {
  font-size: 15px;
  font-weight: bold;
  margin-bottom: 12px;
  padding-left: 8px;
}
</style>