<template>
  <!-- 股票列表页面：筛选搜索 + 统计卡片 + 图表 + 数据表格 -->
  <div class="stock-list">
    <!-- 搜索栏：按股票代码或名称模糊搜索 -->
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="股票代码">
          <el-input v-model="searchForm.code" placeholder="输入股票代码" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="股票名称">
          <el-input v-model="searchForm.name" placeholder="输入股票名称" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 统计数据卡片：总数 / 上涨 / 下跌 / 平均涨幅 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value">{{ stats.total }}</div>
            <div class="stat-label">股票总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value" style="color: #f56c6c">{{ stats.rising }}</div>
            <div class="stat-label">上涨</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value" style="color: #67c23a">{{ stats.falling }}</div>
            <div class="stat-label">下跌</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-value" :style="{ color: stats.avgChange >= 0 ? '#f56c6c' : '#67c23a' }">
              {{ stats.avgChange >= 0 ? '+' : '' }}{{ stats.avgChange }}%
            </div>
            <div class="stat-label">平均涨幅</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ECharts 饼图：涨跌幅分布 -->
    <el-card class="chart-card">
      <template #header>涨跌幅分布</template>
      <div ref="chartRef" class="chart-container"></div>
    </el-card>

    <!-- 股票数据表格 + 分页 -->
    <el-card class="table-card">
      <template #header>股票列表</template>
      <el-table :data="tableData" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="code" label="股票代码" width="120" />
        <el-table-column prop="name" label="股票名称" width="150" />
        <el-table-column prop="price" label="最新价" width="120" />
        <el-table-column prop="change_rate" label="涨跌幅(%)" width="150">
          <!-- 涨跌幅用标签区分涨跌颜色 -->
          <template #default="{ row }">
            <el-tag :type="row.change_rate >= 0 ? 'danger' : 'success'" effect="plain">
              {{ row.change_rate >= 0 ? '+' : '' }}{{ row.change_rate }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="high" label="最高价" width="120" />
        <el-table-column prop="low" label="最低价" width="120" />
        <el-table-column prop="volume" label="成交量" width="150">
          <template #default="{ row }">
            {{ formatVolume(row.volume) }}
          </template>
        </el-table-column>
        <el-table-column prop="turnover" label="成交额(万)" width="150">
          <template #default="{ row }">
            {{ formatTurnover(row.turnover) }}
          </template>
        </el-table-column>
        <el-table-column prop="update_time" label="更新时间" />
      </el-table>

      <!-- 分页组件 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[5, 10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue';
import { getStocks, getStockStats } from '@/api/stock';
import type { StockItem, StockStats } from '@/types';
import * as echarts from 'echarts';

// 表格数据和加载状态
const tableData = ref<StockItem[]>([]);
const loading = ref(false);
const chartRef = ref<HTMLDivElement>();
let chart: echarts.ECharts | null = null;

// 搜索表单和分页参数
const searchForm = reactive({ code: '', name: '' });
const pagination = reactive({ page: 1, size: 10, total: 0 });
const stats = ref<StockStats>({ total: 0, rising: 0, falling: 0, avgChange: 0 });

/** 格式化成交量，超过 10000 显示为 "x.x万" */
function formatVolume(vol: number) {
  if (vol >= 10000) return `${(vol / 10000).toFixed(2)}万`;
  return vol.toString();
}

/** 格式化成交额，添加千位分隔符 */
function formatTurnover(turnover: number) {
  return turnover.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** 拉取股票列表数据 */
async function fetchData() {
  loading.value = true;
  try {
    const res = await getStocks({
      code: searchForm.code,
      name: searchForm.name,
      page: pagination.page,
      size: pagination.size,
    });
    tableData.value = res.data.data.data;
    pagination.total = res.data.data.total;
  } catch {
    // 错误已由 axios 拦截器处理
  } finally {
    loading.value = false;
  }
}

/** 拉取统计数据 + 更新图表 */
async function loadStats() {
  try {
    const res = await getStockStats();
    stats.value = res.data.data;
    updateChart(res.data.data);
  } catch {
    // 错误已由 axios 拦截器处理
  }
}

/** 初始化/更新 ECharts 饼图 */
function updateChart(data: StockStats) {
  if (!chartRef.value) return;
  if (!chart) {
    chart = echarts.init(chartRef.value);
  }

  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { top: '5%', left: 'center' },
    series: [
      {
        name: '涨跌分布',
        type: 'pie',
        radius: ['40%', '70%'],
        data: [
          { value: data.rising, name: '上涨', itemStyle: { color: '#f56c6c' } },
          { value: data.falling, name: '下跌', itemStyle: { color: '#67c23a' } },
          { value: data.total - data.rising - data.falling, name: '平盘', itemStyle: { color: '#909399' } },
        ],
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' },
        },
      },
    ],
  });
}

/** 搜索按钮：重置到第 1 页再查询 */
function handleSearch() {
  pagination.page = 1;
  fetchData();
}

/** 重置按钮：清空表单并查询全部 */
function resetSearch() {
  searchForm.code = '';
  searchForm.name = '';
  pagination.page = 1;
  fetchData();
}

onMounted(() => {
  fetchData();
  loadStats();
  // 窗口缩放时自适应图表大小
  window.addEventListener('resize', () => chart?.resize());
});

// 组件销毁时清理
onBeforeUnmount(() => {
  chart?.dispose();
  window.removeEventListener('resize', () => chart?.resize());
});
</script>

<style scoped>
.stock-list {
  padding: 20px;
}

.search-card {
  margin-bottom: 20px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}

.chart-card {
  margin-bottom: 20px;
}

.chart-container {
  height: 300px;
}

.table-card {
  margin-bottom: 20px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
