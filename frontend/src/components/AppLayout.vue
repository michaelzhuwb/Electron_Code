<template>
  <!-- 整体后台布局：左侧菜单 + 右侧内容区 -->
  <el-container class="app-layout">
    <!-- 左侧导航栏，固定宽度 200px -->
    <el-aside width="200px">
      <!-- 顶部 Logo 区域 -->
      <div class="logo">Michael</div>
      <!-- 菜单，router 模式：点击自动跳转对应路由 -->
      <el-menu
        :default-active="activeMenu"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/">
          <el-icon><HomeFilled /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/stocks">
          <el-icon><DataAnalysis /></el-icon>
          <span>股票列表</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 助手</span>
        </el-menu-item>
        <el-menu-item index="/stock-m">
          <el-icon><Document /></el-icon>
          <span>备选标的</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 右侧主内容区 -->
    <el-container>
      <!-- 顶部标题栏，显示当前页面名称 -->
      <el-header class="app-header">
        <div class="header-title">{{ currentTitle }}</div>
      </el-header>

      <!-- 页面内容渲染区，路由页面在此替换 -->
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
// 引入 Element Plus 图标
import { HomeFilled, DataAnalysis, ChatDotRound, Document } from '@element-plus/icons-vue';

const route = useRoute();

// 根据路由 meta.title 显示当前页面标题
const currentTitle = computed(() => (route.meta.title as string) || 'Client App');
// 高亮当前激活的菜单项（匹配路由路径）
const activeMenu = computed(() => route.path);
</script>

<style scoped>
.app-layout {
  height: 100vh;  /* 铺满整个视口 */
}

.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  font-size: 16px;
  font-weight: bold;
  color: #fff;
  background: #409eff;  /* 主题蓝 */
}

.sidebar-menu {
  border-right: none;  /* 去掉边框，更简洁 */
}

.app-header {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.header-title {
  font-size: 18px;
  font-weight: 500;
}
</style>
