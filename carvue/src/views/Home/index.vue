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
 * 当前激活的标签
 */
const activeTab: Ref<string> = ref<string>('recommend')

/**
 * 核心：执行搜索
 * 跳转到搜索结果页，并携带关键词
 */
const onSearch = () => {
  const keyword = searchKeyword.value.trim()
  if (!keyword) return

  router.push({
    path: '/search-result',
    query: { keyword }
  })
}

/**
 * 功能图标列表 (已映射到真实路由)
 */
interface FunctionIcon {
  id: number
  name: string
  icon: string
  path?: string // 新增：跳转路径
  type?: string // 新增：预设筛选条件
}

const functionIcons: FunctionIcon[] = [
  { id: 1, name: '条件选车', icon: '🔥', path: '/search-result' }, // 去筛选页
  { id: 2, name: '新车上市', icon: '⭐', path: '/buy' },           // 去买新车
  { id: 3, name: '销量排行', icon: '📊', path: '/search-result', type: 'sales' }, // 以后可以加参数
  { id: 4, name: '二手好车', icon: '🚗', path: '/used' },          // 去二手车
  { id: 5, name: '十亿补贴', icon: '🎁', path: '/subsidy' },       // 去补贴页
  { id: 6, name: '查经销商', icon: '🏪', path: '/map' }            // 预留地图页
]

/**
 * 筛选标签列表
 */
const filterTags: Ref<string[]> = ref<string[]>([
  '全部', '奥迪', '宝马', '奔驰', '特斯拉', '比亚迪', '大众'
])
const activeFilterTag: Ref<string> = ref<string>('全部')

/**
 * 处理搜索标签点击 (快捷搜索)
 */
const handleFilterTagClick = (tag: string): void => {
  activeFilterTag.value = tag
  if (tag !== '全部') {
    // 点击标签直接搜
    router.push({
      path: '/search-result',
      query: { keyword: tag }
    })
  }
}

/**
 * 处理功能图标点击
 */
const handleFunctionClick = (item: FunctionIcon): void => {
  if (item.path) {
    router.push(item.path)
  } else {
    console.log('功能开发中:', item.name)
  }
}

// --- 以下保留原来的 Mock 数据，因为后端还没提供 CMS 内容接口 ---

interface ContentItem {
  id: number
  title: string
  image: string
  author: string
  likes: number
  type: 'video' | 'article'
}

const contentList: Ref<ContentItem[]> = ref<ContentItem[]>([
  {
    id: 1,
    title: '奇瑞"不客气"，硬核技术拿下产品定义权',
    image: 'https://via.placeholder.com/350x200/4CAF50/FFFFFF?text=Chery+Tech',
    author: '高动能',
    likes: 192,
    type: 'article'
  },
  {
    id: 2,
    title: '这是比亚迪的什么车型？这外形设计真的太...',
    image: 'https://via.placeholder.com/350x200/2196F3/FFFFFF?text=BYD+New',
    author: '活力马达',
    likes: 498,
    type: 'article'
  }
])

const handleImageSearch = (): void => {
  // 这里可以对接上传图片接口，目前先保留
  console.log('图片搜索功能待开发')
}

const handleContentClick = (item: ContentItem): void => {
  console.log('点击内容:', item.title)
}
</script>

<template>
  <div class="home-page">
    <div class="header">
      <div class="search-container">
        <div class="search-input-wrapper">
          <van-icon name="search" class="search-icon-left" />
          <input
              v-model="searchKeyword"
              class="real-input"
              type="search"
              placeholder="搜索品牌、车型"
              @keyup.enter="onSearch"
          />
          <van-icon name="photograph" class="camera-icon" @click.stop="handleImageSearch" />
        </div>
        <span class="search-btn-text" @click="onSearch">搜索</span>
        <van-icon name="plus" class="action-icon" />
      </div>
    </div>

    <van-tabs
        v-model:active="activeTab"
        swipeable
        sticky
        offset-top="54"
        color="#1989fa"
        title-active-color="#323233"
        title-inactive-color="#969799"
        line-width="20px"
    >
      <van-tab title="关注" name="follow"></van-tab>
      <van-tab title="推荐" name="recommend">
        <div class="content-container">
          <div class="video-banner">
            <img
                src="https://via.placeholder.com/690x400/00ACC1/FFFFFF?text=MG7+Experience"
                alt="动态体验上汽名爵MG7"
                class="banner-image"
            />
            <div class="video-overlay">
              <van-icon name="play-circle-o" class="play-icon" />
            </div>
            <div class="video-info">
              <div class="video-title">动态体验上汽名爵MG7</div>
              <div class="video-subtitle">什么是燃油车的"终极进化"</div>
            </div>
            <div class="video-tag">速度测评</div>
          </div>

          <div class="function-icons">
            <div
                v-for="item in functionIcons"
                :key="item.id"
                class="function-item"
                @click="handleFunctionClick(item)"
            >
              <div class="function-icon">{{ item.icon }}</div>
              <div class="function-name">{{ item.name }}</div>
            </div>
          </div>

          <div class="filter-tags">
            <div
                v-for="tag in filterTags"
                :key="tag"
                :class="['filter-tag', { active: activeFilterTag === tag }]"
                @click="handleFilterTagClick(tag)"
            >
              {{ tag }}
            </div>
          </div>

          <div class="content-list">
            <div
                v-for="item in contentList"
                :key="item.id"
                class="content-item"
                @click="handleContentClick(item)"
            >
              <img :src="item.image" :alt="item.title" class="content-image" />
              <div class="content-info">
                <div class="content-title">{{ item.title }}</div>
                <div class="content-footer">
                  <span class="content-author">{{ item.author }}</span>
                  <div class="content-likes">
                    <van-icon name="good-job-o" />
                    <span>{{ item.likes }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </van-tab>
      <van-tab title="热榜" name="hot"></van-tab>
      <van-tab title="新能源" name="new-energy"></van-tab>
      <van-tab title="购车补贴" name="subsidy"></van-tab>
      <van-tab title="" name="more" disabled>
        <template #title>
          <van-icon name="wap-nav" />
        </template>
      </van-tab>
    </van-tabs>
  </div>
</template>

<style scoped>
.home-page {
  width: 100%;
  min-height: 100vh;
  padding-bottom: 50px;
  background-color: #f7f8fa;
}

/* --- 顶部搜索栏优化 --- */
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 999;
  background-color: #ffffff;
  padding: 8px 12px;
  /* 增加一点阴影让层级更明显 */
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

.search-container {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-input-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  height: 36px;
  background-color: #f2f3f5;
  border-radius: 18px;
  padding: 0 12px;
}

.search-icon-left {
  font-size: 18px;
  color: #969799;
  margin-right: 6px;
}

.real-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 14px;
  color: #323233;
  /* 去掉iOS默认样式 */
  -webkit-appearance: none;
}
.real-input::placeholder {
  color: #c8c9cc;
}

.camera-icon {
  font-size: 20px;
  color: #969799;
  padding-left: 8px;
  border-left: 1px solid #ebedf0;
  margin-left: 4px;
}

.search-btn-text {
  font-size: 15px;
  color: #1989fa; /* 易车蓝 */
  font-weight: 500;
  padding: 0 4px;
}

.action-icon {
  font-size: 22px;
  color: #323233;
}

/* Tabs区域微调 */
:deep(.van-tabs__wrap) {
  position: fixed;
  top: 52px;
  left: 0;
  right: 0;
  z-index: 998;
  background: #fff;
}

/* 内容容器 */
.content-container {
  padding-top: 54px; /* header(52) + tabs(44) 的视觉调整 */
}

/* 视频Banner */
.video-banner {
  position: relative;
  margin: 12px;
  height: 180px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.banner-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.2);
}

.play-icon {
  font-size: 48px;
  color: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(2px);
  border-radius: 50%;
}

.video-info {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px;
  background: linear-gradient(to top, rgba(0,0,0,0.7), transparent);
  color: #ffffff;
}

.video-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 4px;
}

.video-subtitle {
  font-size: 12px;
  opacity: 0.9;
}

.video-tag {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 10px;
  background: rgba(25, 137, 250, 0.9);
  border-radius: 8px;
  font-size: 10px;
  color: #ffffff;
  font-weight: bold;
}

/* 功能图标 */
.function-icons {
  display: grid;
  grid-template-columns: repeat(5, 1fr); /* 5列布局更紧凑 */
  gap: 12px;
  padding: 16px 12px;
  background-color: #ffffff;
  margin-bottom: 8px;
}

.function-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.function-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: #f7f8fa;
  border-radius: 12px;
  transition: transform 0.1s;
}
.function-item:active .function-icon {
  transform: scale(0.95);
  background: #f0f1f2;
}

.function-name {
  font-size: 11px;
  color: #333;
}

/* 筛选标签 */
.filter-tags {
  display: flex;
  gap: 10px;
  padding: 12px;
  background-color: #ffffff;
  overflow-x: auto;
  margin-bottom: 8px;
}
.filter-tags::-webkit-scrollbar { display: none; }

.filter-tag {
  flex-shrink: 0;
  padding: 6px 14px;
  background-color: #f7f8fa;
  border-radius: 14px;
  font-size: 13px;
  color: #646566;
}

.filter-tag.active {
  background-color: #e8f3ff;
  color: #1989fa;
  font-weight: bold;
}

/* 内容列表 (瀑布流布局模拟) */
.content-list {
  padding: 8px;
  column-count: 2; /* CSS多列布局 */
  column-gap: 8px;
}

.content-item {
  background-color: #ffffff;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 8px;
  break-inside: avoid; /* 防止卡片被切断 */
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
}

.content-image {
  width: 100%;
  height: auto; /* 自适应高度 */
  display: block;
}

.content-info {
  padding: 10px;
}

.content-title {
  font-size: 14px;
  color: #333;
  line-height: 1.4;
  margin-bottom: 8px;
  font-weight: 500;
}

.content-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.content-author {
  font-size: 11px;
  color: #999;
}

.content-likes {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  color: #999;
}
</style>