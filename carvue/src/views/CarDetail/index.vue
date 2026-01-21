<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast, showImagePreview } from 'vant'
// ✅ 引入我们刚才定义的 API
import { getCarDetail } from '@/api/car'
import { addHistory, checkFavorite, toggleFavorite } from '@/api/behavior'
import type { ICarProduct } from '@/types'

const route = useRoute()
const router = useRouter()
// 确保 ID 类型安全
const carId = route.params.id as string

const loading = ref(true)
const car = ref<ICarProduct | null>(null)
const currentSwipe = ref(0)

// ❤️ 收藏状态
const isFavorite = ref(false)

// 获取车辆详情
const fetchDetail = async () => {
  try {
    const { data } = await getCarDetail(carId)
    if (data.code === 200) {
      car.value = data.data

      // ✅ 详情获取成功后，立刻检查收藏状态 & 记录足迹
      initUserBehavior()
    } else {
      showToast('车辆信息获取失败')
    }
  } catch (err) {
    console.error(err)
    showToast('网络连接错误')
  } finally {
    loading.value = false
  }
}

// 初始化用户行为 (足迹 + 收藏检查)
const initUserBehavior = async () => {
  // 1. 悄悄记录足迹 (不阻塞 UI，失败也不报错)
  addHistory(carId).catch(() => {
    // 可能是未登录，静默失败即可
  })

  // 2. 检查收藏状态
  try {
    const res = await checkFavorite(carId)
    // 注意：axios 响应结构，res.data 才是后端返回的 json
    isFavorite.value = res.data.is_favorite
  } catch (e) {
    // 未登录或其他错误，默认为未收藏
    isFavorite.value = false
  }
}

// ❤️ 点击收藏按钮
const handleFavorite = async () => {
  try {
    const res = await toggleFavorite(carId)
    isFavorite.value = res.data.is_favorite

    if (isFavorite.value) {
      showToast('已加入收藏')
    } else {
      showToast('已取消收藏')
    }
  } catch (error: any) {
    if (error.response && error.response.status === 401) {
      showToast('请先登录')
      // router.push('/login') // 如果有登录页可以放开
    } else {
      showToast('操作失败')
    }
  }
}

// 图片预览
const handlePreview = (index: number) => {
  if (car.value?.images && car.value.images.length > 0) {
    showImagePreview({
      images: car.value.images,
      startPosition: index
    })
  }
}

onMounted(() => {
  if (carId) {
    fetchDetail()
  }
})
</script>

<template>
  <div class="car-detail-page">
    <van-nav-bar
        title="车辆详情"
        left-arrow
        fixed
        placeholder
        @click-left="router.back()"
    />

    <div v-if="loading" class="loading-box">
      <van-loading vertical type="spinner" color="#1989fa">加载中...</van-loading>
    </div>

    <div v-else-if="car" class="content">
      <div class="hero-swipe">
        <van-swipe class="my-swipe" :autoplay="3000" indicator-color="white" @change="(index: number) => currentSwipe = index">
          <van-swipe-item v-for="(img, index) in (car.images && car.images.length ? car.images : [car.coverImage])" :key="index" @click="handlePreview(index)">
            <img :src="img || 'https://via.placeholder.com/400x300?text=No+Image'" />
          </van-swipe-item>
          <template #indicator>
            <div class="custom-indicator">{{ currentSwipe + 1 }}/{{ (car.images && car.images.length) || 1 }}</div>
          </template>
        </van-swipe>
      </div>

      <div class="info-card">
        <div class="price-row">
          <span class="currency">¥</span>
          <span class="price">{{ car.price }}</span>
          <span class="unit">万</span>
          <span class="guide-label">指导价</span>
        </div>
        <h1 class="car-title">{{ car.name }}</h1>
        <div class="tags-row">
          <van-tag color="#e8f3ff" text-color="#1989fa">{{ car.energy_type }}</van-tag>
          <van-tag color="#f2f3f5" text-color="#333">{{ car.series_level }}</van-tag>
          <van-tag color="#f2f3f5" text-color="#333">{{ car.year }}款</van-tag>
        </div>
      </div>

      <div class="spec-card">
        <div class="card-title">基本信息</div>
        <div class="spec-grid">
          <div class="spec-item">
            <span class="label">品牌</span>
            <span class="value">{{ car.brand_name }}</span>
          </div>
          <div class="spec-item">
            <span class="label">车系</span>
            <span class="value">{{ car.series_name }}</span>
          </div>
          <div class="spec-item">
            <span class="label">销售状态</span>
            <span class="value">{{ car.status === 1 ? '在售' : '停售' }}</span>
          </div>
        </div>
      </div>

      <div style="height: 60px;"></div>
    </div>

    <div v-else class="error-box">
      <van-empty description="未找到车辆信息" />
    </div>

    <van-action-bar>
      <van-action-bar-icon icon="chat-o" text="客服" />

      <van-action-bar-icon
          :icon="isFavorite ? 'star' : 'star-o'"
          :text="isFavorite ? '已收藏' : '收藏'"
          :color="isFavorite ? '#ff5000' : ''"
          @click="handleFavorite"
      />

      <van-action-bar-button type="warning" text="分期方案" />
      <van-action-bar-button type="danger" text="获取底价" />
    </van-action-bar>
  </div>
</template>

<style scoped>
.car-detail-page {
  background: #f7f8fa;
  min-height: 100vh;
}

.loading-box, .error-box {
  padding-top: 150px;
  display: flex;
  justify-content: center;
}

.hero-swipe {
  position: relative;
  height: 240px;
  background: #fff;
}
.my-swipe { height: 100%; }
.my-swipe img { width: 100%; height: 100%; object-fit: cover; }

.custom-indicator {
  position: absolute;
  right: 12px;
  bottom: 12px;
  padding: 2px 8px;
  font-size: 12px;
  color: #fff;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 10px;
}

.info-card {
  margin: 12px;
  padding: 16px;
  background: #fff;
  border-radius: 12px;
}

.price-row {
  color: #ff5000;
  display: flex;
  align-items: baseline;
  margin-bottom: 8px;
}
.currency { font-size: 14px; font-weight: bold; }
.price { font-size: 24px; font-weight: bold; margin: 0 2px; }
.unit { font-size: 14px; margin-right: 6px; }
.guide-label { color: #999; font-size: 12px; text-decoration: line-through; }

.car-title {
  font-size: 18px;
  font-weight: bold;
  color: #333;
  margin-bottom: 12px;
  line-height: 1.4;
}

.tags-row { display: flex; gap: 8px; }

.spec-card {
  margin: 12px;
  padding: 16px;
  background: #fff;
  border-radius: 12px;
}
.card-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 16px;
  position: relative;
  padding-left: 10px;
}
.card-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 4px;
  bottom: 4px;
  width: 4px;
  background: #1989fa;
  border-radius: 2px;
}

.spec-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.spec-item { display: flex; flex-direction: column; gap: 4px; }
.spec-item .label { color: #999; font-size: 12px; }
.spec-item .value { color: #333; font-size: 14px; font-weight: 500; }
</style>