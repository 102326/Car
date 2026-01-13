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
const searchKeyword: Ref<string> = ref<string>('')

/**
 * 快捷功能列表接口
 */
interface QuickFunction {
  id: number
  name: string
  icon: string
}

/**
 * 快捷功能列表
 */
const quickFunctions: QuickFunction[] = [
  { id: 1, name: '国家补贴', icon: '🎁' },
  { id: 2, name: '十亿补贴', icon: '💰' },
  { id: 3, name: '降价排行', icon: '📉' },
  { id: 4, name: '报废补贴', icon: '🚗' },
  { id: 5, name: '当月优惠', icon: '📅' }
]

/**
 * 品牌列表
 */
const brands: string[] = ['奥迪', '五菱汽车', '比亚迪', '万程控股']

/**
 * 价格区间列表
 */
const priceRanges: string[] = ['10万以下', '10-15万', '15-20万', '20-25万', '25万以上']

/**
 * 十亿补贴车型接口
 */
interface SubsidyCar {
  id: number
  name: string
  image: string
  cashback: string
  price: string
}

/**
 * 十亿补贴车型列表
 */
const subsidyCars: SubsidyCar[] = [
  {
    id: 1,
    name: '博越',
    image: 'https://via.placeholder.com/160x120/10b981/FFFFFF?text=Boyue',
    cashback: '500元',
    price: '8.59万起'
  },
  {
    id: 2,
    name: '别克GL8 插混',
    image: 'https://via.placeholder.com/160x120/3b82f6/FFFFFF?text=GL8',
    cashback: '300元',
    price: '24.99万起'
  }
]

/**
 * 政府补贴信息接口
 */
interface GovernmentSubsidy {
  amount: string
  title: string
  description: string
}

/**
 * 政府补贴信息
 */
const governmentSubsidy: GovernmentSubsidy = {
  amount: '15000元',
  title: '北京新能源置换补贴活动',
  description: ''
}

/**
 * 补贴排行车型接口
 */
interface RankingCar {
  id: number
  name: string
  image: string
  subsidy: string
  price: string
}

/**
 * 补贴排行车型列表
 */
const rankingCars: RankingCar[] = [
  {
    id: 1,
    name: '理想L9',
    image: 'https://via.placeholder.com/100x75/8b5cf6/FFFFFF?text=L9',
    subsidy: '75000元',
    price: '40.98万起'
  },
  {
    id: 2,
    name: '理想L8',
    image: 'https://via.placeholder.com/100x75/ec4899/FFFFFF?text=L8',
    subsidy: '70000元',
    price: '32.18万起'
  }
]

/**
 * 热门车型接口
 */
interface HotCar {
  id: number
  brand: string
  name: string
  image: string
  subsidyPolicy: string
  sales: string
  price: string
}

/**
 * 热门车型列表
 */
const hotCars: HotCar[] = [
  {
    id: 1,
    brand: 'volkswagen',
    name: '朗逸',
    image: 'https://via.placeholder.com/340x200/6366f1/FFFFFF?text=Lavida',
    subsidyPolicy: '补贴政策共5000元',
    sales: '12月全国零售量22181辆',
    price: '7.10万起'
  },
  {
    id: 2,
    brand: 'volvo',
    name: '沃尔沃S90',
    image: 'https://via.placeholder.com/340x200/7c3aed/FFFFFF?text=S90',
    subsidyPolicy: '补贴政策共6500元',
    sales: '12月全国零售量2447辆',
    price: '27.99万起'
  }
]

/**
 * 当前选中的品牌筛选
 */
const selectedBrandFilter: Ref<string> = ref<string>('全部')

/**
 * 品牌筛选列表
 */
const brandFilters: string[] = ['全部', '大众', '丰田', '比亚迪', '奥迪', '奔驰', '更多']

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
 * 处理快捷功能点击
 */
const handleQuickFunctionClick = (item: QuickFunction): void => {
  console.log('点击功能:', item.name)
}

/**
 * 处理品牌点击
 */
const handleBrandClick = (brand: string): void => {
  console.log('点击品牌:', brand)
}

/**
 * 处理价格选择
 */
const handlePriceSelect = (price: string): void => {
  console.log('选择价格:', price)
}

/**
 * 处理补贴车型点击
 */
const handleSubsidyCarClick = (car: SubsidyCar): void => {
  console.log('点击补贴车型:', car.name)
}

/**
 * 处理政府补贴领取
 */
const handleClaimSubsidy = (): void => {
  console.log('领取政府补贴')
}

/**
 * 处理排行车型点击
 */
const handleRankingCarClick = (car: RankingCar): void => {
  console.log('点击排行车型:', car.name)
}

/**
 * 处理品牌筛选
 */
const handleBrandFilter = (brand: string): void => {
  selectedBrandFilter.value = brand
  console.log('筛选品牌:', brand)
}

/**
 * 处理热门车型点击
 */
const handleHotCarClick = (car: HotCar): void => {
  console.log('点击热门车型:', car.name)
}

/**
 * 处理查落地价
 */
const handleCheckPrice = (car: HotCar): void => {
  console.log('查落地价:', car.name)
}

/**
 * 处理询底价
 */
const handleAskPrice = (car: HotCar): void => {
  console.log('询底价:', car.name)
}
</script>

<template>
  <div class="subsidy-page">
    <!-- 顶部搜索栏 -->
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
      <div class="search-button" @click="handleSearch">搜索</div>
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

    <!-- 品牌横向滚动 -->
    <div class="brand-scroll">
      <div 
        v-for="(brand, index) in brands" 
        :key="index"
        class="brand-item"
        @click="handleBrandClick(brand)"
      >
        <div class="brand-logo">{{ brand.charAt(0) }}</div>
        <div class="brand-name">{{ brand }}</div>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="content-area">
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

      <!-- 十亿补贴标题 -->
      <div class="section-title-bar">
        <div class="title-text">十亿补贴</div>
      </div>

      <!-- 十亿补贴车型 -->
      <div class="subsidy-cars">
        <div 
          v-for="car in subsidyCars" 
          :key="car.id"
          class="subsidy-car-card"
          @click="handleSubsidyCarClick(car)"
        >
          <div class="cashback-badge">返现</div>
          <div class="cashback-amount">{{ car.cashback }}</div>
          <img :src="car.image" :alt="car.name" class="car-image" />
          <div class="car-name">{{ car.name }}</div>
          <div class="car-price">{{ car.price }}</div>
        </div>
      </div>

      <!-- 政府补贴 -->
      <div class="government-subsidy-section">
        <div class="section-title-bar">
          <div class="title-text">政府补贴</div>
        </div>

        <div class="subsidy-banner">
          <div class="subsidy-amount">{{ governmentSubsidy.amount }}</div>
          <div class="subsidy-info">
            <div class="subsidy-title">{{ governmentSubsidy.title }}</div>
          </div>
          <div class="claim-button" @click="handleClaimSubsidy">领</div>
        </div>
      </div>

      <!-- 补贴排行 -->
      <div class="ranking-section">
        <div class="section-title-bar">
          <div class="title-text">补贴排行</div>
        </div>

        <div class="ranking-cards">
          <div 
            v-for="car in rankingCars" 
            :key="car.id"
            class="ranking-card"
            @click="handleRankingCarClick(car)"
          >
            <img :src="car.image" :alt="car.name" class="ranking-image" />
            <div class="ranking-info">
              <div class="ranking-name">{{ car.name }}</div>
              <div class="ranking-subsidy">
                <span class="subsidy-label">补贴</span>
                <span class="subsidy-value">{{ car.subsidy }}</span>
              </div>
              <div class="ranking-price">{{ car.price }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 品牌筛选 -->
      <div class="brand-filter-section">
        <div class="filter-tabs">
          <div 
            v-for="brand in brandFilters" 
            :key="brand"
            :class="['filter-tab', { active: selectedBrandFilter === brand }]"
            @click="handleBrandFilter(brand)"
          >
            {{ brand }}
          </div>
        </div>
      </div>

      <!-- 热门车型列表 -->
      <div class="hot-cars-section">
        <div 
          v-for="car in hotCars" 
          :key="car.id"
          class="hot-car-card"
          @click="handleHotCarClick(car)"
        >
          <div class="brand-logo-badge">
            <div class="logo-icon">{{ car.brand === 'volkswagen' ? '🚗' : '⭐' }}</div>
            <div class="brand-text">{{ car.brand === 'volkswagen' ? '奥迪' : '沃尔沃' }}</div>
          </div>

          <img :src="car.image" :alt="car.name" class="hot-car-image" />

          <div class="hot-car-content">
            <div class="car-title">{{ car.name }}</div>
            
            <div class="subsidy-policy">{{ car.subsidyPolicy }}</div>
            
            <div class="sales-info">{{ car.sales }}</div>
            
            <div class="price-actions">
              <div class="price-info">
                <div class="price-value">{{ car.price }}</div>
                <div 
                  class="action-button check-price"
                  @click.stop="handleCheckPrice(car)"
                >
                  查落地价
                </div>
              </div>
              <div 
                class="action-button ask-price"
                @click.stop="handleAskPrice(car)"
              >
                询底价
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.subsidy-page {
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
  font-size: 13px;
  color: #323233;
}

.search-input input::placeholder {
  color: #969799;
}

.search-button {
  padding: 6px 12px;
  background: linear-gradient(135deg, #ff6b6b 0%, #e52e2e 100%);
  border-radius: 16px;
  font-size: 13px;
  color: #ffffff;
  cursor: pointer;
}

/* 快捷功能 */
.quick-functions {
  position: fixed;
  top: 52px;
  left: 0;
  right: 0;
  z-index: 998;
  display: flex;
  justify-content: space-around;
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
  font-size: 24px;
}

.function-name {
  font-size: 12px;
  color: #646566;
}

/* 品牌横向滚动 */
.brand-scroll {
  position: fixed;
  top: 120px;
  left: 0;
  right: 0;
  z-index: 997;
  display: flex;
  gap: 16px;
  padding: 12px 16px;
  background-color: #ffffff;
  border-bottom: 1px solid #ebedf0;
  overflow-x: auto;
}

.brand-scroll::-webkit-scrollbar {
  display: none;
}

.brand-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  flex-shrink: 0;
}

.brand-logo {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
  border-radius: 50%;
  font-size: 18px;
  font-weight: bold;
  color: #646566;
}

.brand-name {
  font-size: 11px;
  color: #646566;
  white-space: nowrap;
}

/* 内容区域 */
.content-area {
  margin-top: 190px;
  padding: 0 16px;
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

/* 区块标题 */
.section-title-bar {
  margin-bottom: 12px;
}

.title-text {
  font-size: 18px;
  font-weight: 500;
  color: #323233;
}

/* 十亿补贴车型 */
.subsidy-cars {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.subsidy-car-card {
  position: relative;
  padding: 12px;
  background-color: #ffffff;
  border-radius: 8px;
  cursor: pointer;
}

.cashback-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 2px 8px;
  background-color: #ff6b6b;
  border-radius: 4px;
  font-size: 10px;
  color: #ffffff;
  z-index: 1;
}

.cashback-amount {
  position: absolute;
  top: 28px;
  left: 8px;
  font-size: 12px;
  font-weight: bold;
  color: #ff6b6b;
  z-index: 1;
}

.car-image {
  width: 100%;
  height: 100px;
  object-fit: cover;
  border-radius: 6px;
  margin-bottom: 8px;
}

.car-name {
  font-size: 14px;
  font-weight: 500;
  color: #323233;
  margin-bottom: 4px;
}

.car-price {
  font-size: 13px;
  color: #969799;
}

/* 政府补贴 */
.government-subsidy-section {
  margin-bottom: 20px;
}

.subsidy-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: linear-gradient(135deg, #fff5f0 0%, #ffe8dd 100%);
  border-radius: 8px;
}

.subsidy-amount {
  font-size: 32px;
  font-weight: bold;
  color: #ff6b6b;
}

.subsidy-info {
  flex: 1;
}

.subsidy-title {
  font-size: 14px;
  color: #323233;
}

.claim-button {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ffa500 0%, #ff6b00 100%);
  border-radius: 50%;
  font-size: 20px;
  font-weight: bold;
  color: #ffffff;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(255, 107, 0, 0.3);
}

/* 补贴排行 */
.ranking-section {
  margin-bottom: 20px;
}

.ranking-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.ranking-card {
  padding: 12px;
  background-color: #ffffff;
  border-radius: 8px;
  cursor: pointer;
}

.ranking-image {
  width: 100%;
  height: 80px;
  object-fit: cover;
  border-radius: 6px;
  margin-bottom: 8px;
}

.ranking-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ranking-name {
  font-size: 15px;
  font-weight: 500;
  color: #323233;
}

.ranking-subsidy {
  display: flex;
  align-items: center;
  gap: 4px;
}

.subsidy-label {
  padding: 2px 6px;
  background-color: #ff6b6b;
  border-radius: 4px;
  font-size: 10px;
  color: #ffffff;
}

.subsidy-value {
  font-size: 12px;
  font-weight: bold;
  color: #ff6b6b;
}

.ranking-price {
  font-size: 13px;
  color: #969799;
}

/* 品牌筛选 */
.brand-filter-section {
  margin-bottom: 16px;
}

.filter-tabs {
  display: flex;
  gap: 12px;
  padding: 16px;
  background-color: #ffffff;
  border-radius: 8px;
  overflow-x: auto;
}

.filter-tabs::-webkit-scrollbar {
  display: none;
}

.filter-tab {
  flex-shrink: 0;
  padding: 8px 20px;
  background-color: #f7f8fa;
  border-radius: 20px;
  font-size: 14px;
  color: #646566;
  cursor: pointer;
  transition: all 0.3s;
}

.filter-tab.active {
  background-color: #fff1f0;
  color: #e52e2e;
  font-weight: 500;
}

/* 热门车型列表 */
.hot-cars-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.hot-car-card {
  background-color: #ffffff;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}

.brand-logo-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background-color: #f7f8fa;
}

.logo-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: linear-gradient(135deg, #e0e0e0 0%, #f5f5f5 100%);
  border-radius: 50%;
}

.brand-text {
  font-size: 14px;
  font-weight: 500;
  color: #323233;
}

.hot-car-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
}

.hot-car-content {
  padding: 16px;
}

.car-title {
  font-size: 18px;
  font-weight: 500;
  color: #323233;
  margin-bottom: 8px;
}

.subsidy-policy {
  font-size: 13px;
  color: #ff6b6b;
  margin-bottom: 6px;
}

.sales-info {
  font-size: 12px;
  color: #969799;
  margin-bottom: 12px;
}

.price-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.price-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.price-value {
  font-size: 20px;
  font-weight: bold;
  color: #e52e2e;
}

.action-button {
  padding: 8px 20px;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s;
}

.check-price {
  background: linear-gradient(135deg, #ffa500 0%, #ff6b00 100%);
  color: #ffffff;
}

.ask-price {
  background: linear-gradient(135deg, #ff6b6b 0%, #e52e2e 100%);
  color: #ffffff;
}
</style>

