<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { searchCars, type SearchParams } from '@/api/search'
// ✅ 引入正确的类型定义
import type { ISearchCarProduct, ISearchFacets } from '@/types'

const route = useRoute()
const router = useRouter()

// --- 状态管理 ---
const loading = ref(false)
const finished = ref(false)
const showFilter = ref(false) // 控制筛选弹窗

// ✅ 核心数据 (使用正确的类型)
const carList = ref<ISearchCarProduct[]>([])
const facets = ref<ISearchFacets>({ brands: [], levels: [], energies: [] })
const total = ref(0)

// 搜索参数 (响应式)
const queryParams = reactive<SearchParams>({
  q: (route.query.keyword as string) || '',
  page: 1,
  size: 10,
  sort_by: 'default',
  // 筛选条件
  brand: undefined,
  energy_type: undefined,
  min_price: undefined,
  max_price: undefined
})

// 排序选项
const sortOptions = [
  { text: '综合排序', value: 'default' },
  { text: '价格最低', value: 'price_asc' },
  { text: '价格最高', value: 'price_desc' },
  { text: '最新上架', value: 'new' },
]

// --- 核心方法 ---

// 1. 执行搜索
const doSearch = async (isRefresh = false) => {
  if (isRefresh) {
    queryParams.page = 1
    carList.value = []
    finished.value = false
  }

  loading.value = true
  try {
    const { data } = await searchCars(queryParams)
    if (data.code === 200) {
      // 追加数据
      const { list, total: totalCount, facets: newFacets } = data.data
      carList.value = isRefresh ? list : [...carList.value, ...list]
      total.value = totalCount

      // 更新筛选器选项 (仅第一次或刷新时更新)
      if (isRefresh) {
        facets.value = newFacets
      }

      // 判断是否加载完毕
      if (carList.value.length >= total.value) {
        finished.value = true
      }
    }
  } catch (error) {
    console.error(error)
    showToast('搜索失败，请稍后重试')
    finished.value = true
  } finally {
    loading.value = false
  }
}

// 2. 加载更多
const onLoad = () => {
  queryParams.page++
  doSearch(false)
}

// 3. 处理排序改变
const onSortChange = (value: any) => {
  queryParams.sort_by = value
  doSearch(true)
}

// 4. 处理筛选确认
const onFilterConfirm = () => {
  showFilter.value = false
  doSearch(true)
}

// 5. 顶部搜索栏交互
const handleSearch = () => {
  doSearch(true)
}

const handleClear = () => {
  queryParams.q = ''
  doSearch(true)
}

// --- 生命周期 ---
onMounted(() => {
  doSearch(true)
})

watch(() => route.query.keyword, (newVal) => {
  if (newVal !== queryParams.q) {
    queryParams.q = newVal as string
    doSearch(true)
  }
})
</script>

<template>
  <div class="search-result-page">
    <div class="fixed-header">
      <div class="search-header">
        <van-icon name="arrow-left" class="back-icon" @click="router.back()" />
        <div class="search-input-box">
          <van-icon name="search" />
          <input
              v-model="queryParams.q"
              type="search"
              placeholder="搜一搜有没有你的Dream Car"
              @keyup.enter="handleSearch"
          />
          <van-icon v-if="queryParams.q" name="clear" @click="handleClear" />
        </div>
        <span class="search-btn" @click="handleSearch">搜索</span>
      </div>

      <div class="toolbar">
        <van-dropdown-menu>
          <van-dropdown-item
              v-model="queryParams.sort_by"
              :options="sortOptions"
              @change="onSortChange"
          />
        </van-dropdown-menu>
        <div class="filter-btn" @click="showFilter = true">
          筛选 <van-icon name="filter-o" />
        </div>
      </div>
    </div>

    <div class="content-area">
      <van-list
          v-model:loading="loading"
          :finished="finished"
          finished-text="没有更多了"
          @load="onLoad"
      >
        <div
            v-for="car in carList"
            :key="car.id"
            class="car-card"
            @click="router.push(`/car/${car.id}`)"
        >
          <div class="car-img-box">
            <img :src="car.coverImage" :alt="car.name" />
            <div class="badge" v-if="car.energy_type !== '汽油' && car.energy_type !== '柴油'">新能源</div>
          </div>
          <div class="car-info">
            <h3 class="title" v-html="car.name_highlight || car.name"></h3>
            <div class="tags">
              <span class="tag">{{ car.year }}款</span>
              <span class="tag">{{ car.series_level }}</span>
            </div>
            <div class="price-row">
              <span class="price">¥{{ car.price }}万</span>
              <span class="msrp">指导价</span>
            </div>
          </div>
        </div>
      </van-list>
    </div>

    <van-popup
        v-model:show="showFilter"
        position="right"
        :style="{ width: '80%', height: '100%' }"
    >
      <div class="filter-panel">
        <div class="filter-body">
          <div class="filter-group">
            <div class="group-title">价格区间 (万元)</div>
            <div class="price-inputs">
              <input type="number" v-model.number="queryParams.min_price" placeholder="最低" />
              <span class="divider">-</span>
              <input type="number" v-model.number="queryParams.max_price" placeholder="最高" />
            </div>
          </div>

          <div class="filter-group" v-if="facets.brands?.length">
            <div class="group-title">品牌</div>
            <div class="check-grid">
              <div
                  v-for="brand in facets.brands"
                  :key="brand"
                  class="check-item"
                  :class="{ active: queryParams.brand === brand }"
                  @click="queryParams.brand = (queryParams.brand === brand ? undefined : brand)"
              >
                {{ brand }}
              </div>
            </div>
          </div>

          <div class="filter-group" v-if="facets.energies?.length">
            <div class="group-title">能源类型</div>
            <div class="check-grid">
              <div
                  v-for="energy in facets.energies"
                  :key="energy"
                  class="check-item"
                  :class="{ active: queryParams.energy_type === energy }"
                  @click="queryParams.energy_type = (queryParams.energy_type === energy ? undefined : energy)"
              >
                {{ energy }}
              </div>
            </div>
          </div>
        </div>

        <div class="filter-footer">
          <van-button block round @click="showFilter = false">取消</van-button>
          <van-button block round type="primary" @click="onFilterConfirm">确定</van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.search-result-page {
  padding-top: 100px;
  min-height: 100vh;
  background: #f7f8fa;
}

.fixed-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 99;
  background: #fff;
}

.search-header {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  gap: 12px;
}

.search-input-box {
  flex: 1;
  background: #f2f3f5;
  border-radius: 18px;
  padding: 6px 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.search-input-box input {
  border: none;
  background: transparent;
  width: 100%;
  font-size: 14px;
}

.toolbar {
  display: flex;
  align-items: center;
  border-bottom: 1px solid #eee;
}

:deep(.van-dropdown-menu__bar) {
  box-shadow: none;
}

.filter-btn {
  flex: 1;
  text-align: center;
  font-size: 14px;
  color: #323233;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.content-area {
  padding: 12px;
}

.car-card {
  background: #fff;
  border-radius: 8px;
  margin-bottom: 12px;
  padding: 12px;
  display: flex;
  gap: 12px;
}

.car-img-box {
  width: 120px;
  height: 80px;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
  background-color: #f7f8fa; /* 图片未加载时的背景 */
}

.car-img-box img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.car-img-box .badge {
  position: absolute;
  top: 0;
  left: 0;
  background: #07c160;
  color: #fff;
  font-size: 10px;
  padding: 2px 4px;
  border-bottom-right-radius: 4px;
}

.car-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.title {
  font-size: 16px;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 高亮样式 */
:deep(.text-red-500) {
  color: #ee0a24;
  font-style: normal;
  font-weight: bold;
}

.tags {
  display: flex;
  gap: 6px;
}

.tag {
  background: #f2f3f5;
  color: #666;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 2px;
}

.price {
  color: #ee0a24;
  font-size: 16px;
  font-weight: bold;
  margin-right: 6px;
}

.msrp {
  color: #999;
  font-size: 12px;
}

.filter-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.filter-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.filter-group {
  margin-bottom: 24px;
}

.group-title {
  font-weight: bold;
  margin-bottom: 12px;
  font-size: 14px;
}

.price-inputs {
  display: flex;
  align-items: center;
  gap: 10px;
}

.price-inputs input {
  flex: 1;
  background: #f2f3f5;
  border: none;
  border-radius: 16px;
  padding: 6px 12px;
  text-align: center;
  font-size: 13px;
}

.check-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.check-item {
  background: #f2f3f5;
  padding: 8px 4px;
  text-align: center;
  border-radius: 4px;
  font-size: 12px;
  color: #333;
  border: 1px solid transparent;
}

.check-item.active {
  background: #e8f3ff;
  color: #1989fa;
  border-color: #1989fa;
}

.filter-footer {
  padding: 16px;
  display: flex;
  gap: 12px;
  border-top: 1px solid #eee;
}
</style>