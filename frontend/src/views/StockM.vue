<template>
  <!-- 备选标的页面：筛选栏 + 数据表格 + 分页 -->
  <div class="stock-m-page">
    <!-- 筛选栏：选股日期 / 标签 / 股票代码 -->
    <el-card class="filter-card">
      <el-form :inline="true" class="filter-form">
        <el-form-item label="选股日期">
          <el-select v-model="filterCodeDate" placeholder="请选择" @change="handleFilter" style="width: 150px">
            <el-option label="最新" value="latest" />
            <el-option v-for="d in dates" :key="d" :value="d" :label="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="filterFlag" placeholder="全部" clearable @change="handleFilter" style="width: 150px">
            <el-option v-for="t in tags" :key="t" :value="t" :label="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="股票代码">
          <el-input v-model="filterCode" placeholder="输入代码" clearable @keyup.enter="handleFilter" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleFilter">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格：显示备选标的列表 -->
    <el-card class="table-card">
      <template #header>备选标的</template>
      <el-table :data="tableData" v-loading="loading" stripe style="width: 100%">
        <!-- 选股日期和标签列支持点击排序 -->
        <el-table-column
          prop="code_date"
          label="选股日期"
          width="120"
          sortable="custom"
          @sort-change="handleSort"
        />
        <el-table-column prop="code" label="股票代码" width="120" />
        <el-table-column prop="name" label="股票名称" width="140" />
        <el-table-column prop="change_rate" label="涨跌幅" width="110">
          <!-- 涨跌幅着色：正数红色，负数绿色 -->
          <template #default="{ row }">
            <span :class="changeClass(row.change_rate)">{{ row.change_rate }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="rq_margin_trading" label="融资净买入额" width="140" />
        <el-table-column prop="major_flow" label="主力净流入-净额" width="150" />
        <el-table-column prop="extra_large_flow" label="超大单净流入-净额" width="160" />
        <el-table-column prop="large_flow" label="大单净流入-净额" width="150" />
        <el-table-column prop="code_type" label="形态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.code_type" size="small" type="info">{{ row.code_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="flag"
          label="标签"
          width="140"
          sortable="custom"
          @sort-change="handleSort"
        >
          <template #default="{ row }">
            <el-tag v-if="row.flag" size="small">{{ row.flag }}</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页组件 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { getStockM, getStockMDates, getStockMTags } from '@/api/stock_m';
import type { StockMItem } from '@/api/stock_m';

// 表格数据
const tableData = ref<StockMItem[]>([]);
const loading = ref(false);

// 筛选下拉选项
const dates = ref<string[]>([]);   // 可选日期
const tags = ref<string[]>([]);     // 可选标签

// 筛选条件（用 ref 确保 el-select 响应式更新正常）
const filterCodeDate = ref('latest');
const filterFlag = ref<string | null>(null);
const filterCode = ref('');

// 排序状态
const sortState = ref({
  sort_by: 'date',   // 按日期排序
  sort_order: 'desc', // 降序
});

// 分页参数
const pagination = ref({ page: 1, size: 20, total: 0 });

/** 涨跌幅着色：正数红色，负数绿色 */
function changeClass(val: string) {
  if (!val) return '';
  if (val.startsWith('+')) return 'up';
  if (val.startsWith('-')) return 'down';
  return '';
}

/** 获取所有可选的选股日期 */
async function loadDates() {
  try {
    const res = await getStockMDates();
    dates.value = res.data.data as string[];
  } catch {}
}

/** 获取所有可选的标签 */
async function loadTags() {
  try {
    const res = await getStockMTags();
    tags.value = res.data.data as string[];
  } catch {}
}

/** 拉取备选标的列表数据 */
async function fetchData() {
  loading.value = true;
  try {
    const res = await getStockM({
      // 'latest' 表示取最新日期，传 undefined 让后端默认处理
      code_date: (filterCodeDate.value && filterCodeDate.value !== 'latest') ? filterCodeDate.value : undefined,
      flag: filterFlag.value || undefined,
      code: filterCode.value || undefined,
      sort_by: sortState.value.sort_by,
      sort_order: sortState.value.sort_order,
      page: pagination.value.page,
      size: pagination.value.size,
    });
    tableData.value = res.data.data.data;
    pagination.value.total = res.data.data.total;
  } catch {
    // 错误已由 axios 拦截器处理
  } finally {
    loading.value = false;
  }
}

/** 筛选按钮：重置到第 1 页再查询 */
function handleFilter() {
  pagination.value.page = 1;
  fetchData();
}

/** 重置按钮：恢复默认值并查询 */
function resetFilter() {
  filterCodeDate.value = 'latest';
  filterFlag.value = null;
  filterCode.value = '';
  sortState.value = { sort_by: 'date', sort_order: 'desc' };
  pagination.value.page = 1;
  fetchData();
}

/** 表格排序回调：将列名映射为后端参数 */
function handleSort({ prop, order }: { prop: string; order: string | null }) {
  if (!order) {
    sortState.value.sort_by = 'date';
    sortState.value.sort_order = 'desc';
  } else {
    sortState.value.sort_by = prop === 'code_date' ? 'date' : 'flag';
    sortState.value.sort_order = order === 'ascending' ? 'asc' : 'desc';
  }
  pagination.value.page = 1;
  fetchData();
}

onMounted(() => {
  loadDates();
  loadTags();
  fetchData();
});
</script>

<style scoped>
.stock-m-page {
  padding: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  flex-wrap: wrap;
}

.table-card {
  margin-bottom: 20px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.up {
  color: #f56c6c;   /* 红色：上涨 */
  font-weight: 600;
}

.down {
  color: #67c23a;   /* 绿色：下跌 */
  font-weight: 600;
}
</style>
