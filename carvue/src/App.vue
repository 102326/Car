<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AiAgent from '@/components/AiAgent/index.vue'
/**
 * 当前路由
 */
const route = useRoute()

/**
 * 是否显示底部导航栏
 */
const showTabbar = computed<boolean>(() => {
  const tabbarRoutes: string[] = ['/', '/buy', '/select', '/used', '/mine']
  return tabbarRoutes.includes(route.path)
})
</script>

<template>
  <div id="app">
    <router-view />
    <AiAgent v-if="route.path !== '/login'" />
    
    <!-- 底部导航栏 -->
    <van-tabbar v-if="showTabbar" route active-color="#e52e2e" inactive-color="#7d7e80">
      <van-tabbar-item to="/" icon="wap-home-o">首页</van-tabbar-item>
      <van-tabbar-item to="/buy" icon="shopping-cart-o">买车</van-tabbar-item>
      <van-tabbar-item to="/select" icon="guide-o">选车</van-tabbar-item>
      <van-tabbar-item to="/used" icon="coupon-o">二手车</van-tabbar-item>
      <van-tabbar-item to="/mine" icon="user-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<style scoped>
#app {
  width: 100%;
  height: 100%;
  position: relative;
}
</style>
