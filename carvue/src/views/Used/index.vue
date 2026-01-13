<script setup lang="ts">
import { ref } from 'vue'
import type { Ref } from 'vue'

/**
 * 选中的城市
 */
const selectedCity: Ref<string> = ref<string>('北京')

/**
 * 搜索关键词
 */
const searchKeyword: Ref<string> = ref<string>('钛7 | 小米SU7 | 帕萨特')

/**
 * 功能按钮接口
 */
interface FunctionButton {
  id: number
  icon: string
  name: string
  color: string
}

/**
 * 顶部功能按钮列表
 */
const functionButtons: FunctionButton[] = [
  { id: 1, icon: '🚗', name: '买二手车', color: '#ff6b6b' },
  { id: 2, icon: '💰', name: '我要卖车', color: '#4dabf7' },
  { id: 3, icon: '🔍', name: '帮我找车', color: '#e52e2e' },
  { id: 4, icon: '🔄', name: '置换', color: '#51cf66' },
  { id: 5, icon: '¥', name: '免费估值', color: '#ff9500' }
]

/**
 * 品牌接口
 */
interface BrandItem {
  id: string
  name: string
  logo: string
}

/**
 * 热门品牌列表
 */
const brands: BrandItem[] = [
  { id: 'volkswagen', name: '大众', logo: '🚗' },
  { id: 'byd', name: '比亚迪', logo: '🔋' },
  { id: 'audi', name: '奥迪', logo: '💍' },
  { id: 'benz', name: '奔驰', logo: '⭐' },
  { id: 'bmw', name: '宝马', logo: '🏎️' },
  { id: 'honda', name: '本田', logo: '🔧' },
  { id: 'toyota', name: '丰田', logo: '🚙' },
  { id: 'buick', name: '别克', logo: '🛡️' },
  { id: 'haval', name: '哈弗', logo: '🐺' }
]

/**
 * 价格区间列表
 */
const priceRanges: string[] = ['3万以内', '3-5万', '5-8万', '8-15万', '15-20万']

/**
 * 车型分类列表
 */
const carTypes: string[] = ['SUV', '准新车', '练手车', '城市代步', '更多']

/**
 * 专区入口接口
 */
interface SpecialZone {
  id: number
  title: string
  image: string
  color: string
}

/**
 * 专区入口列表
 */
const specialZones: SpecialZone[] = [
  { id: 1, title: '寄卖驾到', image: '🚚', color: '#e3f2fd' },
  { id: 2, title: '准新车', image: '✨', color: '#fff3e0' },
  { id: 3, title: '降价专区', image: '💰', color: '#fce4ec' },
  { id: 4, title: '一口价', image: '💯', color: '#e0f2f1' }
]

/**
 * 当前激活的标签
 */
const activeTab: Ref<string> = ref<string>('trust')

/**
 * 二手车源接口
 */
interface UsedCar {
  id: number
  name: string
  price: string
  year: string
  mileage: string
  image: string
}

/**
 * 二手车源列表
 */
const usedCarList: UsedCar[] = [
  {
    id: 1,
    name: '凯迪拉克CT6 20...',
    price: '24.98万',
    year: '2024年',
    mileage: '2.00万公里',
    image: 'https://via.placeholder.com/280x180/1e3a8a/FFFFFF?text=CT6'
  },
  {
    id: 2,
    name: '林肯冒险家 202...',
    price: '11.50万',
    year: '2022年',
    mileage: '13.00万公里',
    image: 'https://via.placeholder.com/280x180/065f46/FFFFFF?text=Corsair'
  },
  {
    id: 3,
    name: '奥迪A5 20',
    price: '5.88万',
    year: '2014年',
    mileage: '17.07万公里',
    image: 'https://via.placeholder.com/280x180/b91c1c/FFFFFF?text=A5'
  }
]

/**
 * 处理城市选择
 */
const handleCitySelect = (): void => {
  console.log('选择城市')
}

/**
 * 处理搜索
 */
const handleSearch = (): void => {
  console.log('搜索:', searchKeyword.value)
}

/**
 * 处理定位
 */
const handleLocation = (): void => {
  console.log('定位')
}

/**
 * 处理功能按钮点击
 */
const handleFunctionClick = (item: FunctionButton): void => {
  console.log('点击功能:', item.name)
}

/**
 * 处理品牌选择
 */
const handleBrandSelect = (brand: BrandItem): void => {
  console.log('选择品牌:', brand.name)
}

/**
 * 处理更多品牌
 */
const handleMoreBrands = (): void => {
  console.log('更多品牌')
}

/**
 * 处理价格选择
 */
const handlePriceSelect = (price: string): void => {
  console.log('选择价格:', price)
}

/**
 * 处理车型分类点击
 */
const handleCarTypeClick = (type: string): void => {
  console.log('选择类型:', type)
}

/**
 * 处理专区点击
 */
const handleSpecialZoneClick = (zone: SpecialZone): void => {
  console.log('点击专区:', zone.title)
}

/**
 * 处理车源点击
 */
const handleCarClick = (car: UsedCar): void => {
  console.log('点击车源:', car.name)
}
</script>

<template>
  <div class="used-page">
    <!-- 顶部搜索栏 -->
    <div class="search-bar">
      <div class="city-selector" @click="handleCitySelect">
        <span>{{ selectedCity }}</span>
      </div>
      <div class="search-input">
        <van-icon name="search" />
        <input 
          v-model="searchKeyword"
          type="text"
          placeholder="请输入车型/品牌/城市查询"
          @keyup.enter="handleSearch"
        />
      </div>
      <van-icon name="location-o" class="location-icon" @click="handleLocation" />
    </div>

    <!-- 功能按钮 -->
    <div class="function-buttons">
      <div 
        v-for="item in functionButtons" 
        :key="item.id"
        class="function-button"
        @click="handleFunctionClick(item)"
      >
        <div class="button-icon" :style="{ backgroundColor: item.color }">
          {{ item.icon }}
        </div>
        <div class="button-name">{{ item.name }}</div>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="content-area">
      <!-- 品牌选择 -->
      <div class="brand-section">
        <div class="brand-grid">
          <div 
            v-for="brand in brands" 
            :key="brand.id"
            class="brand-item"
            @click="handleBrandSelect(brand)"
          >
            <div class="brand-logo">{{ brand.logo }}</div>
            <div class="brand-name">{{ brand.name }}</div>
          </div>
          <div class="brand-item more-brands" @click="handleMoreBrands">
            <div class="brand-logo">
              <van-icon name="ellipsis" />
            </div>
            <div class="brand-name">更多</div>
          </div>
        </div>
      </div>

      <!-- 价格筛选 -->
      <div class="price-section">
        <div class="price-tags">
          <div 
            v-for="price in priceRanges" 
            :key="price"
            class="price-tag"
            @click="handlePriceSelect(price)"
          >
            {{ price }}
          </div>
        </div>
      </div>

      <!-- 车型分类 -->
      <div class="car-type-section">
        <div class="type-tags">
          <div 
            v-for="type in carTypes" 
            :key="type"
            class="type-tag"
            @click="handleCarTypeClick(type)"
          >
            {{ type }}
          </div>
        </div>
      </div>

      <!-- 专区入口 -->
      <div class="special-zones">
        <div 
          v-for="zone in specialZones" 
          :key="zone.id"
          class="zone-card"
          :style="{ backgroundColor: zone.color }"
          @click="handleSpecialZoneClick(zone)"
        >
          <div class="zone-icon">{{ zone.image }}</div>
          <div class="zone-title">{{ zone.title }}</div>
        </div>
      </div>

      <!-- 车源标签切换 -->
      <van-tabs 
        v-model:active="activeTab"
        color="#e52e2e"
        title-active-color="#323233"
        title-inactive-color="#969799"
      >
        <van-tab title="放心车" name="trust"></van-tab>
        <van-tab title="一口价" name="fixedprice"></van-tab>
        <van-tab title="视频看车" name="video"></van-tab>
      </van-tabs>

      <!-- 车源列表 -->
      <div class="car-list">
        <div 
          v-for="car in usedCarList" 
          :key="car.id"
          class="car-card"
          @click="handleCarClick(car)"
        >
          <img :src="car.image" :alt="car.name" class="car-image" />
          <div class="car-info">
            <div class="car-name">{{ car.name }}</div>
            <div class="car-meta">{{ car.year }}/{{ car.mileage }}</div>
            <div class="car-price">{{ car.price }}</div>
          </div>
        </div>
      </div>

      <!-- 品牌广告 -->
      <div class="brand-ad">
        <img 
          src="https://via.placeholder.com/690x160/1a365d/FFFFFF?text=LEXUS+二手车官方旗舰店" 
          alt="雷克萨斯二手车"
          class="ad-image"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.used-page {
  width: 100%;
  min-height: 100vh;
  padding-bottom: 50px;
  background-color: #f7f8fa;
}

/* 顶部搜索栏 */
.search-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 999;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #ffffff;
  border-bottom: 1px solid #ebedf0;
}

.city-selector {
  padding: 8px 12px;
  background-color: #f7f8fa;
  border-radius: 16px;
  font-size: 14px;
  color: #323233;
  cursor: pointer;
  white-space: nowrap;
}

.search-input {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 0 12px;
  background-color: #f7f8fa;
  border-radius: 16px;
}

.search-input input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 13px;
  color: #323233;
}

.search-input input::placeholder {
  color: #969799;
}

.location-icon {
  font-size: 20px;
  color: #969799;
  cursor: pointer;
}

/* 功能按钮 */
.function-buttons {
  position: fixed;
  top: 52px;
  left: 0;
  right: 0;
  z-index: 998;
  display: flex;
  justify-content: space-around;
  padding: 16px;
  background-color: #ffffff;
  border-bottom: 1px solid #ebedf0;
}

.function-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.button-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  border-radius: 12px;
  color: #ffffff;
}

.button-name {
  font-size: 12px;
  color: #646566;
}

/* 内容区域 */
.content-area {
  margin-top: 136px;
  padding: 16px;
}

/* 品牌区域 */
.brand-section {
  margin-bottom: 16px;
}

.brand-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  padding: 16px;
  background-color: #ffffff;
  border-radius: 8px;
}

.brand-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.brand-logo {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  background: linear-gradient(135deg, #e0e0e0 0%, #f5f5f5 100%);
  border-radius: 50%;
}

.more-brands .brand-logo {
  background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
  font-size: 24px;
  color: #646566;
}

.brand-name {
  font-size: 12px;
  color: #646566;
  text-align: center;
}

/* 价格筛选 */
.price-section {
  margin-bottom: 16px;
}

.price-tags {
  display: flex;
  gap: 12px;
  padding: 16px;
  background-color: #ffffff;
  border-radius: 8px;
  overflow-x: auto;
}

.price-tags::-webkit-scrollbar {
  display: none;
}

.price-tag {
  flex-shrink: 0;
  padding: 8px 20px;
  background-color: #f7f8fa;
  border-radius: 20px;
  font-size: 14px;
  color: #646566;
  cursor: pointer;
  transition: all 0.3s;
}

.price-tag:active {
  background-color: #fff1f0;
  color: #e52e2e;
}

/* 车型分类 */
.car-type-section {
  margin-bottom: 16px;
}

.type-tags {
  display: flex;
  gap: 12px;
  padding: 16px;
  background-color: #ffffff;
  border-radius: 8px;
  overflow-x: auto;
}

.type-tags::-webkit-scrollbar {
  display: none;
}

.type-tag {
  flex-shrink: 0;
  padding: 8px 20px;
  background-color: #f7f8fa;
  border-radius: 20px;
  font-size: 14px;
  color: #646566;
  cursor: pointer;
  transition: all 0.3s;
}

.type-tag:active {
  background-color: #fff1f0;
  color: #e52e2e;
}

/* 专区入口 */
.special-zones {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.zone-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 80px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.zone-card:active {
  transform: scale(0.95);
}

.zone-icon {
  font-size: 32px;
  margin-bottom: 4px;
}

.zone-title {
  font-size: 13px;
  color: #323233;
  font-weight: 500;
}

/* 车源列表 */
.car-list {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.car-card {
  display: flex;
  gap: 12px;
  padding: 12px;
  background-color: #ffffff;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.car-card:active {
  background-color: #f7f8fa;
}

.car-image {
  width: 140px;
  height: 100px;
  object-fit: cover;
  border-radius: 6px;
}

.car-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.car-name {
  font-size: 15px;
  font-weight: 500;
  color: #323233;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.car-meta {
  font-size: 12px;
  color: #969799;
}

.car-price {
  font-size: 18px;
  font-weight: bold;
  color: #e52e2e;
}

/* 品牌广告 */
.brand-ad {
  margin-top: 16px;
  border-radius: 8px;
  overflow: hidden;
}

.ad-image {
  width: 100%;
  height: auto;
  display: block;
}
</style>
