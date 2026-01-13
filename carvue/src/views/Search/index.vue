<script setup lang="ts">
import { ref } from 'vue'
import type { Ref } from 'vue'
import { useRouter } from 'vue-router'

/**
 * 路由实例
 */
const router = useRouter()

/**
 * 搜索关键词
 */
const searchKeyword: Ref<string> = ref<string>('')

/**
 * 热门搜索标签
 */
const hotSearchTags: string[] = [
  '博越L',
  '星越L',
  '山海L7 PLUS',
  '钛7',
  '小米SU7',
  '帕萨特'
]

/**
 * 历史搜索记录
 */
const historySearchList: Ref<string[]> = ref<string[]>([
  '凯悦刺鸟',
  '凯悦',
  '贝纳利'
])

/**
 * 大家都在看标签
 */
const popularTags: string[] = [
  '途岳',
  '奥迪A4L',
  '长安CS75PLUS',
  '轩逸',
  '探岳',
  '红旗H5',
  '宝马X5',
  '秦PLUS',
  '星越L',
  '帝豪'
]

/**
 * 热点榜数据接口
 */
interface HotNewsItem {
  id: number
  rank: number
  title: string
  tag: 'hot' | 'new' | 'recommend'
  tagText: string
}

/**
 * 热点榜列表
 */
const hotNewsList: HotNewsItem[] = [
  { id: 1, rank: 1, title: '网传小鹏2026年将推出4款...', tag: 'new', tagText: '爆' },
  { id: 2, rank: 2, title: '五菱星光730销量超2万', tag: 'hot', tagText: '热' },
  { id: 3, rank: 3, title: '长城汽车将于1月16日发布...', tag: 'hot', tagText: '热' },
  { id: 4, rank: 4, title: '领克08版型上新', tag: 'recommend', tagText: '荐' },
  { id: 5, rank: 5, title: '2026款北京现代第五代胜达上市', tag: 'hot', tagText: '热' },
  { id: 6, rank: 6, title: '比亚迪海豹08谍照曝光 将于二...', tag: 'hot', tagText: '热' },
  { id: 7, rank: 7, title: '2026款宋Pro DM-i上市', tag: 'hot', tagText: '热' },
  { id: 8, rank: 8, title: '东风日产全新轩逸重产下线', tag: 'hot', tagText: '热' }
]

/**
 * 销量榜数据接口
 */
interface SalesItem {
  id: number
  rank: number
  name: string
  image: string
}

/**
 * 销量榜列表
 */
const salesList: SalesItem[] = [
  { id: 1, rank: 1, name: '特斯拉Model Y', image: 'https://via.placeholder.com/80x60/1976D2/FFFFFF?text=Model+Y' },
  { id: 2, rank: 2, name: '比亚迪秦PLUS', image: 'https://via.placeholder.com/80x60/388E3C/FFFFFF?text=Qin' },
  { id: 3, rank: 3, name: '大众朗逸', image: 'https://via.placeholder.com/80x60/F57C00/FFFFFF?text=Lavida' },
  { id: 4, rank: 4, name: '本田雅阁', image: 'https://via.placeholder.com/80x60/7B1FA2/FFFFFF?text=Accord' },
  { id: 5, rank: 5, name: '丰田凯美瑞', image: 'https://via.placeholder.com/80x60/C62828/FFFFFF?text=Camry' }
]

/**
 * 处理返回
 */
const handleBack = (): void => {
  router.back()
}

/**
 * 处理搜索
 */
const handleSearch = (): void => {
  if (searchKeyword.value.trim()) {
    // 添加到历史记录
    if (!historySearchList.value.includes(searchKeyword.value)) {
      historySearchList.value.unshift(searchKeyword.value)
    }
    console.log('搜索:', searchKeyword.value)
    // 跳转到搜索结果页
    router.push(`/search-result?keyword=${searchKeyword.value}`)
  }
}

/**
 * 处理热门标签点击
 */
const handleHotTagClick = (tag: string): void => {
  searchKeyword.value = tag
  handleSearch()
}

/**
 * 处理历史记录点击
 */
const handleHistoryClick = (keyword: string): void => {
  searchKeyword.value = keyword
  handleSearch()
}

/**
 * 删除单个历史记录
 */
const handleDeleteHistory = (index: number): void => {
  historySearchList.value.splice(index, 1)
}

/**
 * 清空历史记录
 */
const handleClearHistory = (): void => {
  historySearchList.value = []
}

/**
 * 处理热门标签点击
 */
const handlePopularTagClick = (tag: string): void => {
  searchKeyword.value = tag
  handleSearch()
}

/**
 * 处理热点新闻点击
 */
const handleHotNewsClick = (item: HotNewsItem): void => {
  console.log('点击热点新闻:', item.title)
}

/**
 * 处理销量榜点击
 */
const handleSalesClick = (item: SalesItem): void => {
  console.log('点击销量榜:', item.name)
}

/**
 * 获取标签样式类名
 */
const getTagClass = (tag: 'hot' | 'new' | 'recommend'): string => {
  const classMap: Record<string, string> = {
    hot: 'tag-hot',
    new: 'tag-new',
    recommend: 'tag-recommend'
  }
  return classMap[tag] || ''
}

/**
 * 获取排名样式类名
 */
const getRankClass = (rank: number): string => {
  return rank <= 3 ? 'rank-top' : 'rank-normal'
}
</script>

<template>
  <div class="search-page">
    <!-- 顶部搜索栏 -->
    <div class="search-header">
      <van-icon name="arrow-left" class="back-icon" @click="handleBack" />
      <div class="search-box">
        <van-icon name="search" />
        <input 
          v-model="searchKeyword"
          type="search"
          placeholder="星越L"
          autofocus
          @keyup.enter="handleSearch"
        />
      </div>
      <div class="search-button" @click="handleSearch">搜索</div>
    </div>

    <!-- 内容区域 -->
    <div class="search-content">
      <!-- 热门搜索 -->
      <div class="hot-search-section">
        <div class="hot-tags">
          <div 
            v-for="(tag, index) in hotSearchTags" 
            :key="index"
            class="hot-tag"
            @click="handleHotTagClick(tag)"
          >
            {{ tag }}
          </div>
        </div>
      </div>

      <!-- 历史搜索 -->
      <div v-if="historySearchList.length > 0" class="history-section">
        <div class="section-header">
          <div class="section-title">历史搜索</div>
          <van-icon name="delete-o" class="clear-icon" @click="handleClearHistory" />
        </div>
        <div class="history-tags">
          <div 
            v-for="(keyword, index) in historySearchList" 
            :key="index"
            class="history-tag"
            @click="handleHistoryClick(keyword)"
          >
            {{ keyword }}
          </div>
        </div>
      </div>

      <!-- 大家都在看 -->
      <div class="popular-section">
        <div class="section-header">
          <div class="section-title">大家都在看</div>
          <van-icon name="replay" class="refresh-icon" />
        </div>
        <div class="popular-tags">
          <div 
            v-for="(tag, index) in popularTags" 
            :key="index"
            class="popular-tag"
            @click="handlePopularTagClick(tag)"
          >
            {{ tag }}
          </div>
        </div>
      </div>

      <!-- 内容是否满意 -->
      <div class="feedback-section">
        <span class="feedback-text">您对内容是否满意</span>
        <div class="feedback-action">
          <van-icon name="edit" />
          <span>意见反馈</span>
        </div>
      </div>

      <!-- 榜单区域 -->
      <div class="ranking-section">
        <div class="ranking-tabs">
          <div class="ranking-tab active">
            <div class="tab-title">热点榜</div>
            <div class="tab-action">
              更多
              <van-icon name="arrow" />
            </div>
          </div>
          <div class="ranking-tab">
            <div class="tab-title">销量榜</div>
          </div>
        </div>

        <!-- 热点榜列表 -->
        <div class="hot-news-list">
          <div 
            v-for="item in hotNewsList" 
            :key="item.id"
            class="hot-news-item"
            @click="handleHotNewsClick(item)"
          >
            <div :class="['rank-number', getRankClass(item.rank)]">{{ item.rank }}</div>
            <div class="news-content">
              <div class="news-title">{{ item.title }}</div>
              <div :class="['news-tag', getTagClass(item.tag)]">{{ item.tagText }}</div>
            </div>
          </div>
        </div>

        <!-- 销量榜列表 -->
        <div class="sales-list">
          <div 
            v-for="item in salesList" 
            :key="item.id"
            class="sales-item"
            @click="handleSalesClick(item)"
          >
            <div :class="['rank-number', getRankClass(item.rank)]">{{ item.rank }}</div>
            <img :src="item.image" :alt="item.name" class="car-image" />
            <div class="car-name">{{ item.name }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.search-page {
  width: 100%;
  min-height: 100vh;
  background-color: #f7f8fa;
}

/* 顶部搜索栏 */
.search-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background-color: #ffffff;
  border-bottom: 1px solid #ebedf0;
}

.back-icon {
  font-size: 20px;
  color: #323233;
  cursor: pointer;
}

.search-box {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 12px;
  background-color: #f7f8fa;
  border-radius: 18px;
}

.search-box input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: #323233;
}

.search-box input::placeholder {
  color: #969799;
}

.search-button {
  font-size: 14px;
  color: #323233;
  cursor: pointer;
}

/* 内容区域 */
.search-content {
  padding: 16px;
}

/* 热门搜索 */
.hot-search-section {
  margin-bottom: 20px;
}

.hot-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.hot-tag {
  padding: 8px 16px;
  background-color: #ffffff;
  border-radius: 20px;
  font-size: 14px;
  color: #323233;
  cursor: pointer;
  transition: all 0.3s;
}

.hot-tag:active {
  background-color: #f7f8fa;
}

/* 历史搜索 */
.history-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-title {
  font-size: 16px;
  font-weight: 500;
  color: #323233;
}

.clear-icon,
.refresh-icon {
  font-size: 18px;
  color: #969799;
  cursor: pointer;
}

.history-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.history-tag {
  padding: 8px 16px;
  background-color: #ffffff;
  border-radius: 20px;
  font-size: 14px;
  color: #646566;
  cursor: pointer;
  transition: all 0.3s;
}

.history-tag:active {
  background-color: #f7f8fa;
}

/* 大家都在看 */
.popular-section {
  margin-bottom: 20px;
}

.popular-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.popular-tag {
  padding: 8px 16px;
  background-color: #ffffff;
  border-radius: 20px;
  font-size: 14px;
  color: #646566;
  cursor: pointer;
  transition: all 0.3s;
}

.popular-tag:active {
  background-color: #f7f8fa;
}

/* 内容反馈 */
.feedback-section {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 20px 0;
  margin-bottom: 20px;
}

.feedback-text {
  font-size: 14px;
  color: #969799;
}

.feedback-action {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: #1989fa;
  cursor: pointer;
}

/* 榜单区域 */
.ranking-section {
  background-color: #ffffff;
  border-radius: 8px;
  overflow: hidden;
}

.ranking-tabs {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  border-bottom: 1px solid #ebedf0;
}

.ranking-tab {
  padding: 16px;
  border-right: 1px solid #ebedf0;
}

.ranking-tab:last-child {
  border-right: none;
}

.ranking-tab.active {
  background-color: #fff7f7;
}

.tab-title {
  font-size: 16px;
  font-weight: 500;
  color: #323233;
  margin-bottom: 8px;
}

.tab-action {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #969799;
}

/* 热点榜列表 */
.hot-news-list {
  padding: 0 16px;
}

.hot-news-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 0;
  border-bottom: 1px solid #f7f8fa;
  cursor: pointer;
}

.hot-news-item:last-child {
  border-bottom: none;
}

.rank-number {
  width: 20px;
  font-size: 16px;
  font-weight: bold;
  text-align: center;
}

.rank-number.rank-top {
  color: #e52e2e;
}

.rank-number.rank-normal {
  color: #969799;
}

.news-content {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.news-title {
  flex: 1;
  font-size: 14px;
  color: #323233;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.news-tag {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: #ffffff;
}

.news-tag.tag-hot {
  background-color: #ff6b6b;
}

.news-tag.tag-new {
  background-color: #ff6b6b;
}

.news-tag.tag-recommend {
  background-color: #ffa502;
}

/* 销量榜列表 */
.sales-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  padding: 16px;
}

.sales-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.car-image {
  width: 100%;
  height: 80px;
  object-fit: cover;
  border-radius: 6px;
}

.car-name {
  font-size: 13px;
  color: #323233;
  text-align: center;
}
</style>

