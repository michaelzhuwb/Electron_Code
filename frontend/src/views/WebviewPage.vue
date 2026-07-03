<template>
  <div class="webview-page">
    <div class="webview-toolbar">
      <el-input v-model="url" placeholder="输入网址，例如 https://www.baidu.com" style="flex: 1; margin-right: 8px;" @keyup.enter="loadUrl" />
      <el-button type="primary" @click="loadUrl">加载</el-button>
      <el-button type="info" @click="showScript = !showScript">{{ showScript ? '隐藏' : '注入' }}</el-button>
    </div>

    <!-- 注入脚本面板 -->
    <transition name="slide-down">
      <div v-if="showScript" class="script-panel">
        <el-tabs v-model="scriptTab">
          <el-tab-pane label="CSS 注入" name="css">
            <el-input
              v-model="store.webviewCss"
              type="textarea"
              :rows="4"
              placeholder="输入 CSS，例如：.sidebar { display: none !important; }"
              style="margin-bottom: 8px;"
            />
            <el-button size="small" type="primary" @click="doInsertCss">注入 CSS</el-button>
            <el-button size="small" @click="store.webviewCss = ''">清空</el-button>
          </el-tab-pane>
          <el-tab-pane label="JS 注入" name="js">
            <el-input
              v-model="injectJs"
              type="textarea"
              :rows="4"
              placeholder="输入 JavaScript，例如：document.querySelector('.nav')?.remove()"
              style="margin-bottom: 8px;"
            />
            <el-button size="small" type="primary" @click="doExecuteJs">执行 JS</el-button>
            <el-button size="small" @click="injectJs = ''">清空</el-button>
          </el-tab-pane>
        </el-tabs>
        <div class="script-hints">
          <el-alert title="常用示例" type="info" :closable="false" show-icon>
            <template #default>
              <div>1. 隐藏侧边栏: <code>.sidebar, .nav, .menu { display: none !important; }</code></div>
              <div>2. 隐藏顶部导航: <code>header, .header, .navbar { display: none !important; }</code></div>
              <div>3. 全屏内容区: <code>.main, .content { width: 100% !important; padding: 0 !important; }</code></div>
            </template>
          </el-alert>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useDashboardStore } from '@/stores/dashboard';

const store = useDashboardStore();

// 绑定 store 中的 URL，输入即同步
const url = ref(store.webviewUrl);
watch(url, (val) => { store.webviewUrl = val; });
watch(() => store.webviewUrl, (val) => { url.value = val; });

const showScript = ref(false);
const scriptTab = ref('css');
const injectJs = ref('');

const api = (window as any).electronAPI;

function loadUrl() {
  let u = url.value.trim();
  if (!u.startsWith('http://') && !u.startsWith('https://')) {
    u = 'https://' + u;
  }
  url.value = u;
}

/** 注入 CSS */
async function doInsertCss() {
  if (!store.webviewCss.trim()) return;
  const wcId = await api.webviewGetId();
  if (!wcId) return;
  await api.webviewInsertCSS(wcId, store.webviewCss, 'user-css');
}

/** 执行 JS */
async function doExecuteJs() {
  if (!injectJs.value.trim()) return;
  const wcId = await api.webviewGetId();
  if (!wcId) return;
  await api.webviewExecuteJS(wcId, injectJs.value);
}
</script>

<style scoped>
.webview-page {
  background: #f5f5f5;
}

.webview-toolbar {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  gap: 8px;
}

.script-panel {
  padding: 12px 16px;
  background: #fafafa;
  border-bottom: 1px solid #e4e7ed;
}

.script-hints {
  margin-top: 8px;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.2s ease;
}
.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  max-height: 0;
}
</style>
