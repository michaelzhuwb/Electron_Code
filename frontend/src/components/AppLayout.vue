<template>
  <!-- 整体后台布局：自定义标题栏 + 左侧菜单 + 右侧内容区 -->
  <div class="app-layout">
    <!-- 自定义标题栏：Logo + 页面标题 + 窗口控制按钮 -->
    <div class="custom-titlebar" data-tauri-drag-region>
      <div class="titlebar-left">
        <!-- 应用图标和名称 -->
        <div class="titlebar-logo">Michael</div>
        <!-- 当前页面标题 -->
        <div class="titlebar-page">{{ currentTitle }}</div>
      </div>
      <!-- 窗口控制按钮：菜单 / 最小化 / 最大化 / 关闭 -->
      <div class="titlebar-controls">
        <!-- 菜单下拉按钮 -->
        <div class="control-btn menu-btn" @click="showMenu = !showMenu" title="菜单">
          <svg viewBox="0 0 12 12" width="14" height="14">
            <circle cx="6" cy="3" r="1" fill="currentColor" />
            <circle cx="6" cy="6" r="1" fill="currentColor" />
            <circle cx="6" cy="9" r="1" fill="currentColor" />
          </svg>
        </div>
        <div class="control-btn minimize-btn" @click="onMinimize" title="最小化">
          <svg viewBox="0 0 12 12" width="12" height="12">
            <line x1="0" y1="6" x2="12" y2="6" stroke="currentColor" stroke-width="1" />
          </svg>
        </div>
        <div
          class="control-btn maximize-btn"
          @click="onMaximize"
          :title="isMaximized ? '还原' : '最大化'"
        >
          <svg v-if="!isMaximized" viewBox="0 0 12 12" width="12" height="12">
            <rect x="1" y="1" width="10" height="10" fill="none" stroke="currentColor" stroke-width="1" />
          </svg>
          <svg v-else viewBox="0 0 12 12" width="12" height="12">
            <rect x="0" y="2" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1" />
            <path d="M4 10 L10 10 L10 4" fill="none" stroke="currentColor" stroke-width="1" />
          </svg>
        </div>
        <div class="control-btn close-btn" @click="onClose" title="关闭">
          <svg viewBox="0 0 12 12" width="12" height="12">
            <line x1="1" y1="1" x2="11" y2="11" stroke="currentColor" stroke-width="1" />
            <line x1="11" y1="1" x2="1" y2="11" stroke="currentColor" stroke-width="1" />
          </svg>
        </div>
        <!-- 下拉菜单面板 -->
        <transition name="dropdown">
          <div v-if="showMenu" class="dropdown-menu" @click.stop>
            <div class="dropdown-item" @click="onMenuItem('settings')">⚙️ 设 置</div>
            <div class="dropdown-item" @click="onMenuItem('notifications')">🔔 消 息</div>
            <div class="dropdown-divider"></div>
            <div class="dropdown-item" @click="onMenuItem('about')">ℹ️ 关 于</div>
          </div>
        </transition>
      </div>
    </div>

    <!-- 下方区域：左侧菜单 + 右侧内容 -->
    <div class="app-body" @click="onClickOutside">
      <!-- 左侧导航栏，固定宽度 200px -->
      <div class="sidebar">
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
          <el-menu-item index="/data-analysis">
            <el-icon><TrendCharts /></el-icon>
            <span>数据分析</span>
          </el-menu-item>
          <el-menu-item index="/stock-m">
            <el-icon><Document /></el-icon>
            <span>备选标的</span>
          </el-menu-item>
          <el-menu-item index="/chat">
            <el-icon><Document /></el-icon>
            <span>AI助手</span>
          </el-menu-item>
        </el-menu>
      </div>

      <!-- 右侧主内容区 -->
      <div class="main-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
// 引入 Element Plus 图标
import { HomeFilled, TrendCharts, Document } from '@element-plus/icons-vue';

const route = useRoute();

// 根据路由 meta.title 显示当前页面标题
const currentTitle = computed(() => (route.meta.title as string) || 'Client App');
// 高亮当前激活的菜单项（匹配路由路径）
const activeMenu = computed(() => route.path);

// 窗口是否最大化
const isMaximized = ref(false);
// 右上角下拉菜单显示状态
const showMenu = ref(false);

// 获取 electron API（由 preload.js 注入）
const api = (window as any).electronAPI;

/** 窗口最小化 */
function onMinimize() {
  api.minimizeWindow();
}

/** 窗口最大化/还原 */
async function onMaximize() {
  api.maximizeWindow();
  isMaximized.value = await api.isMaximized();
}

/** 关闭窗口 */
function onClose() {
  api.closeWindow();
}

/** 右上角菜单项点击 */
function onMenuItem(action: string) {
  showMenu.value = false;
  if (action === 'about') {
    alert('Michael Client v1.0.0');
  } else if (action === 'settings') {
    // 暂未实现，可后续扩展
  } else if (action === 'notifications') {
    // 暂未实现，可后续扩展
  }
}

/** 点击页面其他区域关闭下拉菜单 */
function onClickOutside() {
  if (showMenu.value) showMenu.value = false;
}

onMounted(async () => {
  // 初始化最大化状态
  isMaximized.value = await api.isMaximized();
  // 监听系统窗口大小变化来判断是否最大化（拖拽窗口时）
  window.addEventListener('resize', async () => {
    isMaximized.value = await api.isMaximized();
  });
});
</script>

<style scoped>
.app-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ========== 自定义标题栏 ========== */
.custom-titlebar {
  height: 40px;
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  background: #1a1a2e;
  color: #e0e0e0;
  user-select: none;
  -webkit-user-select: none;
  /* 整个标题栏可拖拽 */
  -webkit-app-region: drag;
  flex-shrink: 0;
}

.titlebar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-left: 12px;
  height: 100%;
}

.titlebar-logo {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #409eff;
}

.titlebar-page {
  font-size: 12px;
  color: #909399;
  border-left: 1px solid #444;
  padding-left: 12px;
}

.titlebar-controls {
  display: flex;
  align-items: stretch;
  height: 100%;
  position: relative;
  /* 控制按钮区域不可拖拽 */
  -webkit-app-region: no-drag;
}

.control-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 100%;
  color: #e0e0e0;
  cursor: pointer;
  transition: background 0.15s;
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.control-btn:active {
  background: rgba(255, 255, 255, 0.15);
}

/* 关闭按钮悬停变红色 */
.close-btn:hover {
  background: #e44040;
  color: #fff;
}

/* ========== 右上角下拉菜单 ========== */
.dropdown-menu {
  position: absolute;
  top: 40px;
  right: calc(46px * 3);
  min-width: 140px;
  background: #1a1a2e;
  border: 1px solid #333;
  border-radius: 4px;
  padding: 4px 0;
  z-index: 9999;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  -webkit-app-region: no-drag;
}

.dropdown-item {
  padding: 8px 16px;
  font-size: 13px;
  color: #e0e0e0;
  cursor: pointer;
  transition: background 0.15s;
}

.dropdown-item:hover {
  background: rgba(64, 158, 255, 0.15);
  color: #409eff;
}

.dropdown-divider {
  height: 1px;
  margin: 4px 0;
  background: #333;
}

/* 下拉菜单展开动画 */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}

.dropdown-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}

.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ========== 下方主体区域 ========== */
.app-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.sidebar {
  width: 200px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  overflow-y: auto;
}

.sidebar-menu {
  border-right: none;
  height: 100%;
}

.main-content {
  flex: 1;
  overflow: auto;
  background: #f5f5f5;
}
</style>
