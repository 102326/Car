<script setup lang="ts">
import { ref } from 'vue'
import type { Ref } from 'vue'

/**
 * 当前选中的顶部Tab
 */
const activeTopTab: Ref<string> = ref<string>('newcar')

/**
 * 选中的城市
 */
const selectedCity: Ref<string> = ref<string>('北京')

/**
 * 搜索关键词
 */
const searchKeyword: Ref<string> = ref<string>('星越L')

/**
 * 当前选中的品牌
 */
const selectedBrand: Ref<string> = ref<string>('')

/**
 * 当前选中的价格区间
 */
const selectedPrice: Ref<string> = ref<string>('')

/**
 * 是否只看新能源
 */
const onlyNewEnergy: Ref<boolean> = ref<boolean>(false)

/**
 * 是否只看在售
 */
const onlyOnSale: Ref<boolean> = ref<boolean>(true)

/**
 * 快捷功能列表
 */
interface QuickFunction {
  id: number
  name: string
  icon: string
}

const quickFunctions: QuickFunction[] = [
  { id: 1, name: '销量排行', icon: '📊' },
  { id: 2, name: '条件选车', icon: '🔥' },
  { id: 3, name: '新车上市', icon: '⭐' },
  { id: 4, name: '国家补贴', icon: '¥' },
  { id: 5, name: '附近经销商', icon: '🏪' },
  { id: 6, name: '热榜', icon: '🔥' }
]

/**
 * 品牌列表
 */
interface BrandItem {
  id: string
  name: string
  logo: string
}

const brands: BrandItem[] = [
  { id: 'volkswagen', name: '大众', logo: '🚗' },
  { id: 'toyota', name: '丰田', logo: '🚙' },
  { id: 'audi', name: '奥迪', logo: '🏎️' },
  { id: 'benz', name: '奔驰', logo: '🚘' },
  { id: 'bmw', name: '宝马', logo: '🚕' }
]

/**
 * 价格区间列表
 */
const priceRanges: string[] = ['5万以下', '5-8万', '8-15万', '15-20万']

/**
 * 车型分类列表
 */
const carTypes: string[] = ['新能源', 'SUV', '轿车', '更多条件']

/**
 * 推荐车型接口
 */
interface CarItem {
  id: number
  name: string
  image: string
  tag?: string
}

/**
 * 猜你喜欢车型列表
 */
const recommendCars: CarItem[] = [
  { id: 1, name: '坦克300', image: 'https://via.placeholder.com/160x120/F44336/FFFFFF?text=Tank300' },
  { id: 2, name: '雅阁', image: 'https://via.placeholder.com/160x120/2196F3/FFFFFF?text=Accord' },
  { id: 3, name: '红旗H5', image: 'https://via.placeholder.com/160x120/4CAF50/FFFFFF?text=H5' },
  { id: 4, name: '迈腾', image: 'https://via.placeholder.com/160x120/FF9800/FFFFFF?text=Magotan' },
  { id: 5, name: '朗逸', image: 'https://via.placeholder.com/160x120/9C27B0/FFFFFF?text=Lavida' },
  { id: 6, name: '帕萨特', image: 'https://via.placeholder.com/160x120/00BCD4/FFFFFF?text=Passat' }
]

/**
 * 热门车型接口
 */
interface HotCarItem {
  id: number
  name: string
  price: string
  image: string
  subtitle?: string
  badge?: string
}

/**
 * 热门车型列表
 */
const hotCars: HotCarItem[] = [
  {
    id: 1,
    name: 'Model Y',
    price: '3.05万',
    subtitle: '查最低价',
    image: 'https://via.placeholder.com/340x200/1976D2/FFFFFF?text=Model+Y'
  },
  {
    id: 2,
    name: '秦PLUS',
    price: '17.82万',
    subtitle: '查最低价',
    image: 'https://via.placeholder.com/340x200/388E3C/FFFFFF?text=Qin+PLUS'
  }
]

/**
 * 字母索引列表
 */
const alphabetList: string[] = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')

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
 * 处理图片搜索
 */
const handleImageSearch = (): void => {
  console.log('图片搜索')
}

/**
 * 处理快捷功能点击
 */
const handleQuickFunctionClick = (item: QuickFunction): void => {
  console.log('点击功能:', item.name)
}

/**
 * 处理品牌选择
 */
const handleBrandSelect = (brand: BrandItem): void => {
  selectedBrand.value = brand.id
  console.log('选择品牌:', brand.name)
}

/**
 * 处理价格区间选择
 */
const handlePriceSelect = (price: string): void => {
  selectedPrice.value = price
  console.log('选择价格:', price)
}

/**
 * 处理车型分类点击
 */
const handleCarTypeClick = (type: string): void => {
  console.log('选择类型:', type)
}

/**
 * 处理车型点击
 */
const handleCarClick = (car: CarItem | HotCarItem): void => {
  console.log('点击车型:', car.name)
}

/**
 * 处理字母索引点击
 */
const handleAlphabetClick = (letter: string): void => {
  console.log('点击字母:', letter)
}
</script>

<template>
  <div class="buy-page">
    <!-- 顶部分类Tab -->
    <van-tabs 
      v-model:active="activeTopTab" 
      sticky
      color="#e52e2e"
      title-active-color="#323233"
      title-inactive-color="#969799"
      class="top-tabs"
    >
      <van-tab title="新车" name="newcar"></van-tab>
      <van-tab title="新能源" name="newenergy"></van-tab>
      <van-tab title="十亿补贴" name="subsidy"></van-tab>
      <van-tab title="摩托车" name="motorcycle"></van-tab>
      <van-tab title="豪华品牌" name="luxury"></van-tab>
    </van-tabs>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <div class="city-selector" @click="handleCitySelect">
        <span>{{ selectedCity }}</span>
        <van-icon name="arrow-down" />
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
      <van-icon name="photo-o" class="camera-icon" @click="handleImageSearch" />
    </div>

    <!-- 快捷功能 -->
    <div class="quick-functions">
      <div 
        v-for="item in quickFunctions" 
        :key="item.id"
        class="function-item"
        @click="handleQuickFunctionClick(item)"
      >
        <div class="function-icon">{{ item.icon }}</div>
        <div class="function-name">{{ item.name }}</div>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="content-area">
      <!-- 字母索引 -->
      <div class="alphabet-index">
        <div 
          v-for="letter in alphabetList" 
          :key="letter"
          class="alphabet-item"
          @click="handleAlphabetClick(letter)"
        >
          {{ letter }}
        </div>
      </div>

      <!-- 品牌选择 -->
      <div class="brand-section">
        <div class="brand-grid">
          <div 
            v-for="brand in brands" 
            :key="brand.id"
            :class="['brand-item', { active: selectedBrand === brand.id }]"
            @click="handleBrandSelect(brand)"
          >
            <div class="brand-logo">{{ brand.logo }}</div>
            <div class="brand-name">{{ brand.name }}</div>
          </div>
        </div>
      </div>

      <!-- 价格区间 -->
      <div class="price-section">
        <div class="price-tags">
          <div 
            v-for="price in priceRanges" 
            :key="price"
            :class="['price-tag', { active: selectedPrice === price }]"
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

      <!-- 猜你喜欢 -->
      <div class="recommend-section">
        <div class="section-title">猜你喜欢</div>
        <div class="car-grid">
          <div 
            v-for="car in recommendCars" 
            :key="car.id"
            class="car-card"
            @click="handleCarClick(car)"
          >
            <div class="ad-tag">广告</div>
            <img :src="car.image" :alt="car.name" class="car-image" />
            <div class="car-name">{{ car.name }}</div>
          </div>
        </div>
      </div>

      <!-- 热门车型 -->
      <div class="hot-cars-section">
        <div 
          v-for="car in hotCars" 
          :key="car.id"
          class="hot-car-card"
          @click="handleCarClick(car)"
        >
          <img :src="car.image" :alt="car.name" class="hot-car-image" />
          <div class="hot-car-info">
            <div class="hot-car-name">{{ car.name }}</div>
            <div class="hot-car-price">
              <span class="price-label">成交价</span>
              <span class="price-value">{{ car.price }}</span>
            </div>
            <div class="hot-car-action">{{ car.subtitle }}</div>
          </div>
        </div>
      </div>

      <!-- 筛选开关 -->
      <div class="filter-switches">
        <div class="switch-item">
          <span>只看</span>
          <span class="highlight">新能源⚡</span>
          <van-switch v-model="onlyNewEnergy" size="20px" active-color="#e52e2e" />
        </div>
        <div class="switch-item">
          <span>只看在售</span>
          <van-switch v-model="onlyOnSale" size="20px" active-color="#e52e2e" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.buy-page {
  width: 100%;
  min-height: 100vh;
  padding-bottom: 50px;
  background-color: #f7f8fa;
}

/* 顶部Tab */
.top-tabs {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 999;
  background-color: #ffffff;
}

/* 搜索栏 */
.search-bar {
  position: fixed;
  top: 44px;
  left: 0;
  right: 0;
  z-index: 998;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #ffffff;
  border-bottom: 1px solid #ebedf0;
}

.city-selector {
  display: flex;
  align-items: center;
  gap: 4px;
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
  font-size: 14px;
  color: #323233;
}

.search-input input::placeholder {
  color: #969799;
}

.camera-icon {
  font-size: 20px;
  color: #969799;
  cursor: pointer;
}

/* 快捷功能 */
.quick-functions {
  position: fixed;
  top: 88px;
  left: 0;
  right: 0;
  z-index: 997;
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  padding: 12px 16px;
  background-color: #ffffff;
  border-bottom: 1px solid #ebedf0;
}

.function-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.function-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
  border-radius: 10px;
}

.function-name {
  font-size: 11px;
  color: #646566;
  text-align: center;
}

/* 内容区域 */
.content-area {
  margin-top: 172px;
  padding: 0 16px;
  position: relative;
}

/* 字母索引 */
.alphabet-index {
  position: fixed;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 996;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px;
  background-color: rgba(255, 255, 255, 0.9);
  border-radius: 12px 0 0 12px;
}

.alphabet-item {
  width: 20px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: #646566;
  cursor: pointer;
}

.alphabet-item:hover {
  color: #e52e2e;
  font-weight: bold;
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
  transition: all 0.3s;
}

.brand-item.active .brand-logo {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  transform: scale(1.1);
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
  transition: all 0.3s;
}

.brand-name {
  font-size: 12px;
  color: #646566;
}

/* 价格区间 */
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

.price-tag.active {
  background-color: #fff1f0;
  color: #e52e2e;
  font-weight: 500;
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
}

.type-tag {
  flex: 1;
  padding: 10px 16px;
  background-color: #f7f8fa;
  border-radius: 20px;
  font-size: 14px;
  color: #646566;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.type-tag:hover {
  background-color: #fff1f0;
  color: #e52e2e;
}

/* 猜你喜欢 */
.recommend-section {
  margin-bottom: 16px;
}

.section-title {
  font-size: 18px;
  font-weight: 500;
  color: #323233;
  margin-bottom: 12px;
}

.car-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.car-card {
  position: relative;
  background-color: #ffffff;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}

.ad-tag {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 2px 8px;
  background-color: rgba(0, 0, 0, 0.6);
  border-radius: 4px;
  font-size: 10px;
  color: #ffffff;
  z-index: 1;
}

.car-image {
  width: 100%;
  height: 80px;
  object-fit: cover;
}

.car-name {
  padding: 8px;
  font-size: 13px;
  color: #323233;
  text-align: center;
}

/* 热门车型 */
.hot-cars-section {
  margin-bottom: 16px;
}

.hot-car-card {
  display: flex;
  gap: 12px;
  padding: 16px;
  background-color: #ffffff;
  border-radius: 8px;
  margin-bottom: 12px;
  cursor: pointer;
}

.hot-car-image {
  width: 140px;
  height: 90px;
  object-fit: cover;
  border-radius: 6px;
}

.hot-car-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.hot-car-name {
  font-size: 16px;
  font-weight: 500;
  color: #323233;
}

.hot-car-price {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.price-label {
  font-size: 12px;
  color: #969799;
}

.price-value {
  font-size: 20px;
  font-weight: bold;
  color: #e52e2e;
}

.hot-car-action {
  display: inline-block;
  padding: 6px 16px;
  background: linear-gradient(135deg, #ff6b6b 0%, #e52e2e 100%);
  border-radius: 16px;
  font-size: 12px;
  color: #ffffff;
  text-align: center;
  cursor: pointer;
}

/* 筛选开关 */
.filter-switches {
  display: flex;
  justify-content: space-between;
  padding: 16px;
  background-color: #ffffff;
  border-radius: 8px;
  margin-bottom: 16px;
}

.switch-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #323233;
}

.highlight {
  color: #e52e2e;
  font-weight: 500;
}
</style>
