/**
 * Vite 配置文件
 * - 启用 Vue3 + Element Plus + 自动导入组件/指令
 * - 配置 @ 别名指向 src 目录
 * - 开发环境代理 /api 请求到后端 Python 服务
 */
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import AutoImport from 'unplugin-auto-import/vite';
import Components from 'unplugin-vue-components/vite';
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers';
import path from 'path';

export default defineConfig({
  plugins: [
    vue(),
    // 自动导入 Element Plus 的组件和指令（无需手动 import）
    AutoImport({
      resolvers: [ElementPlusResolver()],
    }),
    Components({
      resolvers: [ElementPlusResolver()],
    }),
  ],
  resolve: {
    alias: {
      // @ → frontend/src，方便导入
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    // 开发环境代理：前端请求 /api/* 会转发到后端 Python
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:18000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',  // 打包输出目录
  },
});
