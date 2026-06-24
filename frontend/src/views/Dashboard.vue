<template>
  <!-- 首页仪表盘 -->
  <div class="dashboard">
    <!-- 顶部提示卡片 -->
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>欢迎使用 Client App</span>
            </div>
          </template>
          <p>框架已就绪。按以下步骤添加新功能：</p>
          <ol>
            <li>在 <code>backend/routers/</code> 创建 API 路由文件</li>
            <li>在 <code>backend/main.py</code> 注册路由</li>
            <li>在 <code>frontend/src/views/</code> 创建页面组件</li>
            <li>在 <code>frontend/src/router/index.ts</code> 添加路由</li>
            <li>在 <code>frontend/src/api/index.ts</code> 添加 API 方法</li>
          </ol>
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="20">
      <el-col>
      <el-card>
        <!-- <ul style="list-style: none;"><li v-for="(value, key) in backendData"> -->
        <ol><li v-for="(value, key) in backendData">
          <b>{{ key }}: </b>&nbsp;{{ value }}
        </li>
      </ol>
      </el-card>
      </el-col>
    </el-row>
    <!-- 后端状态检测 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>后端状态</template>
          <div v-if="backendStatus">{{ backendStatus }}</div>
          <div v-else>检测中...</div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { healthCheck } from '@/api';
import { List } from 'echarts';

// 存储后端状态文本
const backendStatus = ref<string>('');
const backendData = ref<any>({})

onMounted(async () => {
  try {
    // 调用健康检查接口，成功则显示在线状态
    const res = await healthCheck();
    backendStatus.value = `在线 (${res.data.data.status})`;
    backendData.value = res.data.data.urls
  } catch {
    backendStatus.value = '离线 - 请检查后端服务';
  }
});
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}
</style>
