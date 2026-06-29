/**
 * Vue Router 配置
 * 使用 Hash 模式（createWebHashHistory），兼容 Electron 加载本地文件
 */
import { createRouter, createWebHashHistory } from 'vue-router';

const router = createRouter({
  // Hash 模式避免 Electron 中 SPA 路由刷新 404
  history: createWebHashHistory(),
  routes: [
    // 首页仪表盘
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { title: '首页' },
    },
    // 股票实时行情
    {
      path: '/stocks',
      name: 'StockList',
      component: () => import('@/views/StockList.vue'),
      meta: { title: '股票列表' },
    },
    // DeepSeek AI 助手
    {
      path: '/chat',
      name: 'Chat',
      component: () => import('@/views/Chat.vue'),
      meta: { title: 'AI 助手' },
    },
    // 备选标的列表
    {
      path: '/stock-m',
      name: 'StockM',
      component: () => import('@/views/StockM.vue'),
      meta: { title: '备选标的' },
    },
    // 数据分析：市场概况 + 两融-主力数据
    {
      path: '/data-analysis',
      name: 'DataAnalysis',
      component: () => import('@/views/DataAnalysis.vue'),
      meta: { title: '数据分析' },
    },
  ],
});

// 全局路由守卫：切换页面时更新浏览器标题
router.beforeEach((to, _from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - Client App`;
  }
  next();
});

export default router;
