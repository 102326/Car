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
 * 功能图标列表
 */
interface FunctionIcon {
  id: number
  name: string
  icon: string
}

const functionIcons: FunctionIcon[] = [
  { id: 1, name: '条件选车', icon: '🔥' },
  { id: 2, name: '新车上市', icon: '⭐' },
  { id: 3, name: '销量排行', icon: '📊' },
  { id: 4, name: '热度排行', icon: '📈' },
  { id: 5, name: '十亿补贴', icon: '🎁' },
  { id: 6, name: '查经销商', icon: '🏪' }
]

/**
 * 筛选标签列表
 */
const filterTags: Ref<string[]> = ref<string[]>([
  '全部',
  'RAV4荣放',
  '朗逸',
  '奥迪Q5L',
  '奥迪A6L',
  '帕萨特',
  '宝马3系'
])

/**
 * 当前选中的筛选标签
 */
const activeFilterTag: Ref<string> = ref<string>('全部')

/**
 * 内容列表数据接口
 */
interface ContentItem {
  id: number
  title: string
  image: string
  author: string
  likes: number
  type: 'video' | 'article'
}

/**
 * 内容列表
 */
const contentList: Ref<ContentItem[]> = ref<ContentItem[]>([
  {
    id: 1,
    title: '奇瑞"不客气"，硬核技术拿下产品定义权',
    image: 'https://via.placeholder.com/350x200/4CAF50/FFFFFF?text=Car+Image+1',
    author: '高动能',
    likes: 192,
    type: 'article'
  },
  {
    id: 2,
    title: '这是比亚迪的什么车型？这外形设计真的太...',
    image: 'https://via.placeholder.com/350x200/2196F3/FFFFFF?text=Car+Image+2',
    author: '活力马达',
    likes: 498,
    type: 'article'
  }
])

/**
 * 处理搜索
 */
const handleSearch = (): void => {
  router.push('/search')
}

/**
 * 处理图片搜索
 */
const handleImageSearch = (): void => {
  console.log('图片搜索')
}

/**
 * 处理功能图标点击
 */
const handleFunctionClick = (item: FunctionIcon): void => {
  console.log('点击功能:', item.name)
}

/**
 * 处理筛选标签点击
 */
const handleFilterTagClick = (tag: string): void => {
  activeFilterTag.value = tag
}

/**
 * 处理内容项点击
 */
const handleContentClick = (item: ContentItem): void => {
  console.log('点击内容:', item.title)
}
</script>

<template>
  <div class="home-page">
    <!-- 顶部搜索栏 -->
    <div class="header">
      <div class="search-container">
        <div class="search-box" @click="handleSearch">
          <van-icon name="photo-o" class="camera-icon" @click.stop="handleImageSearch" />
          <span class="search-text">星越L</span>
        </div>
        <van-icon name="minus" class="action-icon" />
        <van-icon name="plus" class="action-icon" />
      </div>
    </div>

    <!-- 标签导航 -->
    <van-tabs 
      v-model:active="activeTab" 
      swipeable
      sticky
      offset-top="50"
      color="#e52e2e"
      title-active-color="#323233"
      title-inactive-color="#969799"
    >
      <van-tab title="关注" name="follow"></van-tab>
      <van-tab title="推荐" name="recommend">
        <div class="content-container">
          <!-- 视频Banner -->
          <div class="video-banner">
            <img 
              src="https://via.placeholder.com/690x400/00ACC1/FFFFFF?text=MG7+Video" 
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

          <!-- 功能图标 -->
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

          <!-- 筛选标签 -->
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

          <!-- 内容列表 -->
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
      <van-tab title="精品" name="quality"></van-tab>
      <van-tab title="国家补贴" name="subsidy"></van-tab>
      <van-tab title="" name="more">
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

/* 顶部搜索栏 */
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 999;
  background-color: #ffffff;
  padding: 8px 16px;
  border-bottom: 1px solid #ebedf0;
}

.search-container {
  display: flex;
  align-items: center;
  gap: 12px;
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
  cursor: pointer;
}

.camera-icon {
  font-size: 20px;
  color: #969799;
}

.search-text {
  flex: 1;
  font-size: 14px;
  color: #323233;
}

.action-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f7f8fa;
  border-radius: 50%;
  font-size: 18px;
  color: #323233;
  cursor: pointer;
}

/* Tabs区域预留顶部空间 */
:deep(.van-tabs) {
  padding-top: 52px;
}

:deep(.van-tabs__wrap) {
  position: fixed;
  top: 52px;
  left: 0;
  right: 0;
  z-index: 998;
}

/* 内容容器 */
.content-container {
  padding-top: 44px;
}

/* 视频Banner */
.video-banner {
  position: relative;
  width: 100%;
  height: 200px;
  margin-bottom: 12px;
  border-radius: 8px;
  overflow: hidden;
}

.banner-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
}

.play-icon {
  font-size: 48px;
  color: #ffffff;
}

.video-info {
  position: absolute;
  bottom: 12px;
  left: 12px;
  right: 12px;
  color: #ffffff;
}

.video-title {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 4px;
}

.video-subtitle {
  font-size: 13px;
  opacity: 0.9;
}

.video-tag {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  font-size: 12px;
  color: #ffffff;
}

/* 功能图标 */
.function-icons {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  padding: 16px;
  background-color: #ffffff;
  margin-bottom: 8px;
}

.function-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.function-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
  border-radius: 12px;
}

.function-name {
  font-size: 12px;
  color: #646566;
  text-align: center;
}

/* 筛选标签 */
.filter-tags {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  background-color: #ffffff;
  overflow-x: auto;
  white-space: nowrap;
  margin-bottom: 8px;
}

.filter-tags::-webkit-scrollbar {
  display: none;
}

.filter-tag {
  flex-shrink: 0;
  padding: 6px 16px;
  background-color: #f7f8fa;
  border-radius: 16px;
  font-size: 14px;
  color: #646566;
  cursor: pointer;
  transition: all 0.3s;
}

.filter-tag.active {
  background-color: #fff1f0;
  color: #e52e2e;
  font-weight: 500;
}

/* 内容列表 */
.content-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  padding: 0 8px 16px;
}

.content-item {
  background-color: #ffffff;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}

.content-image {
  width: 100%;
  height: 120px;
  object-fit: cover;
}

.content-info {
  padding: 8px;
}

.content-title {
  font-size: 13px;
  color: #323233;
  line-height: 1.4;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.content-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.content-author {
  font-size: 12px;
  color: #969799;
}

.content-likes {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #969799;
}
</style>

