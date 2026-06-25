<template>
  <!-- 首页仪表盘 -->
  <div class="dashboard">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 第一个页签：欢迎页面 -->
      <el-tab-pane label="首页" name="welcome">
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
      </el-tab-pane>

      <!-- 第二个页签：融资融券数据 -->
      <el-tab-pane label="两融-主力数据" name="margin">
        <div class="margin-panel">
          <!-- 查询条件 -->
          <el-form inline class="search-form">
            <el-form-item label="股票代码">
              <el-input v-model="searchCode" placeholder="请输入股票代码" style="width: 160px;" @keyup.enter="loadMarginData" />
            </el-form-item>
            <el-form-item label="查询日期">
              <el-date-picker v-model="searchDate" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 160px;" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadMarginData" :loading="loading">查询</el-button>
            </el-form-item>
          </el-form>

          <!-- 数据展示 -->
          <el-card v-if="marginData" shadow="hover">
            <template #header>
              <div class="card-header">
                <span>{{ marginData.code }} - {{ marginData.tradeDate }}</span>
              </div>
            </template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="代码">{{ marginData.code }}</el-descriptions-item>
              <el-descriptions-item label="日期">{{ marginData.tradeDate }}</el-descriptions-item>
              <el-descriptions-item label="收盘价">{{ marginData.closePrice }}</el-descriptions-item>
              <el-descriptions-item label="涨跌幅">{{ marginData.changeRate }}%</el-descriptions-item>
              <el-descriptions-item label="主力净流入-净额">{{ marginData.majorFlow }}</el-descriptions-item>
              <el-descriptions-item label="超大单净流入-净额">{{ marginData.extraLargeFlow }}</el-descriptions-item>
              <el-descriptions-item label="大单净流入-净额">{{ marginData.largeFlow }}</el-descriptions-item>
              <el-descriptions-item label="融资净买入">{{ marginData.marginNetBuy }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
          <el-empty v-else-if="!loading" description="请输入股票代码后查询" />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { healthCheck } from '@/api';
import { until_test } from '@/api/untils';

// 当前激活的页签
const activeTab = ref('welcome');

// 存储后端状态文本
const backendStatus = ref<string>('');
const backendData = ref<any>({});

// 两融数据查询条件
const searchCode = ref('002049');
const searchDate = ref('');
const loading = ref(false);

// 合并后的两融数据
interface MarginData {
  code: string;
  tradeDate: string;
  closePrice: string;
  changeRate: string;
  majorFlow: string;       // 主力净流入-净额
  extraLargeFlow: string;  // 超大单净流入-净额
  largeFlow: string;       // 大单净流入-净额
  marginNetBuy: string;    // 融资净买入
}
const marginData = ref<MarginData | null>(null);

onMounted(async () => {
  try {
    // 调用健康检查接口，成功则显示在线状态
    const res = await healthCheck();
    backendStatus.value = `在线 (${res.data.data.status})`;
    backendData.value = res.data.data.urls;
  } catch {
    backendStatus.value = '离线 - 请检查后端服务';
  }
});

/** 查询两融数据 */
async function loadMarginData() {
  loading.value = true;
  try {
    const res = await until_test({
      code: searchCode.value,
      code_date: searchDate.value || undefined,
    });
    const data = res.data.data;
    const margin = data.margin_flow as any;
    const major = data.major_flow as any;

    // 合并 margin_flow 和 major_flow 中的关键字段
    marginData.value = {
      code: margin['代码'] ?? major['代码'] ?? '-',
      tradeDate: margin['交易时间'] ?? margin['日期'] ?? major['日期'] ?? '-',
      closePrice: major['收盘价'] ?? '-',
      changeRate: major['涨跌幅'] != null ? `${major['涨跌幅']}` : '-',
      majorFlow: major['主力净流入-净额'] ?? '-',
      extraLargeFlow: major['超大单净流入-净额'] ?? '-',
      largeFlow: major['大单净流入-净额'] ?? '-',
      marginNetBuy: margin['融资净买入'] ?? '-',
    };
  } catch {
    marginData.value = null;
  } finally {
    loading.value = false;
  }
}
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

.margin-panel {
  padding: 10px 0;
}

.search-form {
  margin-bottom: 20px;
}
</style>
