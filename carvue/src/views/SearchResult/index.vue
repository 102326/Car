<script setup lang="ts">
import { ref } from 'vue'
import type { Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/**
 * 路由实例
 */
const route = useRoute()
const router = useRouter()

/**
 * 搜索关键词
 */
const searchKeyword: Ref<string> = ref<string>(route.query.keyword as string || '凯悦刺鸟')

/**
 * 当前激活的Tab
 */
const activeTab: Ref<string> = ref<string>('all')

/**
 * Tab列表
 */
const tabs: Array<{ name: string; label: string }> = [
  { name: 'all', label: '全部' },
  { name: 'newcar', label: '新车' },
  { name: 'video', label: '视频' },
  { name: 'article', label: '图文' },
  { name: 'shorts', label: '小视频' },
  { name: 'more', label: '更多' }
]

/**
 * AI回答是否完成
 */
const aiAnswerComplete: Ref<boolean> = ref<boolean>(true)

/**
 * AI回答内容
 */
const aiAnswerContent: Ref<string> = ref<string>(`凯悦刺鸟是一款高性价比的250cc双缸仿赛摩托车，以下是其特点：

·外观设计：延续凯悦家族战斗风格，线条流畅且肌肉感十足。锐利前脸搭配犀利大灯，攻击性满满，夜间骑行辨识度超高。同时提供多种配色，满足不同审美需求。

·动力性能：搭载249cc直列双缸水冷发动机，最大功率24kW/11500rpm，最大扭矩22.5N·m/9000rpm，官方零百加速6.5秒，极速可达160km/h。动力输出平顺，震动小，日常通勤轻松，跑山也能满足速度渴望。

·操控性能：采用WSBK赛车同平台轻量化钻石菱形一体式车架，整备质量仅147kg，灵活性出色。前倒置减震（37mm）不可调，后中置减震（38mm）预载可调，整体调教偏运动，过弯支撑性好。

·安全配置：标配双通道ABS和TCS牵引力控制系统，提升紧急刹车和湿滑路面骑行的安全性。前320mm单盘配凯悦自研双活塞浮动卡钳，后220mm单盘配单活塞浮动卡钳，制动效果强劲。正新CST S1米其林轮胎`)

/**
 * 处理返回
 */
const handleBack = (): void => {
  router.back()
}

/**
 * 处理清除搜索
 */
const handleClearSearch = (): void => {
  searchKeyword.value = ''
}

/**
 * 处理搜索
 */
const handleSearch = (): void => {
  console.log('搜索:', searchKeyword.value)
}
</script>

<template>
  <div class="search-result-page">
    <!-- 顶部搜索栏 -->
    <div class="search-header">
      <van-icon name="arrow-left" class="back-icon" @click="handleBack" />
      <div class="search-box">
        <van-icon name="search" />
        <input 
          v-model="searchKeyword"
          type="search"
          placeholder="请输入搜索关键词"
          @keyup.enter="handleSearch"
        />
        <van-icon 
          v-if="searchKeyword" 
          name="clear" 
          class="clear-icon" 
          @click="handleClearSearch" 
        />
      </div>
      <div class="search-button" @click="handleSearch">搜索</div>
    </div>

    <!-- Tab导航 -->
    <van-tabs 
      v-model:active="activeTab"
      sticky
      offset-top="52"
      color="#e52e2e"
      title-active-color="#323233"
      title-inactive-color="#969799"
      class="result-tabs"
    >
      <van-tab 
        v-for="tab in tabs" 
        :key="tab.name"
        :title="tab.label" 
        :name="tab.name"
      >
        <!-- AI小易回答 -->
        <div class="ai-section">
          <div class="ai-header">
            <div class="ai-logo">
              <div class="logo-icon">Ai</div>
              <span class="logo-text">小易</span>
            </div>
            <div v-if="aiAnswerComplete" class="complete-badge">
              <van-icon name="success" />
              <span>完成回答</span>
            </div>
          </div>

          <div class="ai-answer">
            <div class="answer-title">
              凯悦刺鸟是一款高性价比的250cc双缸仿赛摩托车，以下是其特点：
            </div>

            <div class="answer-content">
              <div class="content-section">
                <div class="section-title">·外观设计</div>
                <div class="section-text">
                  ：延续凯悦家族战斗风格，线条流畅且肌肉感十足。锐利前脸搭配犀利大灯，攻击性满满，夜间骑行辨识度超高。同时提供多种配色，满足不同审美需求。
                </div>
              </div>

              <div class="content-section">
                <div class="section-title">·动力性能</div>
                <div class="section-text">
                  ：搭载249cc直列双缸水冷发动机，最大功率24kW/11500rpm，最大扭矩22.5N·m/9000rpm，官方零百加速6.5秒，极速可达160km/h。动力输出平顺，震动小，日常通勤轻松，跑山也能满足速度渴望。
                </div>
              </div>

              <div class="content-section">
                <div class="section-title">·操控性能</div>
                <div class="section-text">
                  ：采用WSBK赛车同平台轻量化钻石菱形一体式车架，整备质量仅147kg，灵活性出色。前倒置减震（37mm）不可调，后中置减震（38mm）预载可调，整体调教偏运动，过弯支撑性好。
                </div>
              </div>

              <div class="content-section">
                <div class="section-title">·安全配置</div>
                <div class="section-text">
                  ：标配双通道ABS和TCS牵引力控制系统，提升紧急刹车和湿滑路面骑行的安全性。前320mm单盘配凯悦自研双活塞浮动卡钳，后220mm单盘配单活塞浮动卡钳，制动效果强劲。正新CST S1米其林轮胎
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 其他搜索结果内容占位 -->
        <div class="other-results">
          <div class="placeholder-text">其他搜索结果加载中...</div>
        </div>
      </van-tab>
    </van-tabs>
  </div>
</template>

<style scoped>
.search-result-page {
  width: 100%;
  min-height: 100vh;
  background-color: #f7f8fa;
}

/* 顶部搜索栏 */
.search-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
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

.clear-icon {
  font-size: 16px;
  color: #969799;
  cursor: pointer;
}

.search-button {
  font-size: 14px;
  color: #323233;
  cursor: pointer;
}

/* Tab导航 */
.result-tabs {
  margin-top: 52px;
}

:deep(.van-tabs__wrap) {
  position: fixed;
  top: 52px;
  left: 0;
  right: 0;
  z-index: 999;
}

:deep(.van-tabs__content) {
  margin-top: 44px;
}

/* AI回答区域 */
.ai-section {
  padding: 16px;
  background-color: #ffffff;
  margin-bottom: 8px;
}

.ai-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.ai-logo {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  font-size: 14px;
  font-weight: bold;
  color: #ffffff;
}

.logo-text {
  font-size: 16px;
  font-weight: 500;
  color: #323233;
}

.complete-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  background-color: #f0f9ff;
  border-radius: 12px;
  font-size: 12px;
  color: #1989fa;
}

.complete-badge .van-icon {
  font-size: 14px;
}

/* AI回答内容 */
.ai-answer {
  line-height: 1.8;
}

.answer-title {
  font-size: 15px;
  font-weight: 500;
  color: #323233;
  margin-bottom: 12px;
  line-height: 1.6;
}

.answer-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.content-section {
  font-size: 14px;
  color: #646566;
  line-height: 1.8;
}

.section-title {
  display: inline;
  font-weight: 500;
  color: #323233;
}

.section-text {
  display: inline;
}

/* 其他结果 */
.other-results {
  padding: 40px 16px;
  text-align: center;
}

.placeholder-text {
  font-size: 14px;
  color: #969799;
}
</style>
