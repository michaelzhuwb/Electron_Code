<template>
  <!-- 数据分析：市场概况 + 两融主力数据 -->
  <div class="data-analysis">
    <el-tabs v-model="store.activeTab" type="border-card">
      <!-- 市场概况 -->
      <el-tab-pane label="市场概况" name="market">
        <div class="market-panel">
          <div class="market-header-row">
            <el-button type="primary" @click="loadMarketOverview" :loading="store.marketLoading">刷新数据</el-button>
            <span v-if="store.marketSuggestion" class="market-suggestion">{{ store.marketSuggestion }}</span>
          </div>

          <!-- 涨跌停统计 -->
          <el-row :gutter="20" v-if="store.marketOverview">
            <el-col :span="8">
              <el-card shadow="hover">
                <template #header>涨跌停统计</template>
                <el-row :gutter="20">
                  <el-col :span="12" v-for="item in zdtItems" :key="item.label">
                    <div class="stat-item">
                      <div class="stat-label">{{ item.label }}</div>
                      <div class="stat-value" :class="item.cls">{{ store.marketOverview[item.key] }}</div>
                    </div>
                  </el-col>
                </el-row>
              </el-card>
            </el-col>

            <!-- 涨跌幅分布 -->
            <el-col :span="16">
              <el-card shadow="hover">
                <template #header>涨跌幅分布</template>
                <div class="zdfb-list" v-if="store.marketOverview">
                  <div v-for="(_, idx) in zdfbLabels" :key="idx" class="zdfb-row">
                    <span class="zdfb-label" :class="zdfbLabelClass(idx)">{{ zdfbLabels[idx].label }}</span>
                    <div class="zdfb-bar-wrapper">
                      <div class="zdfb-bar" :style="{ width: zdfbPercentage(store.marketOverview.zdfb[idx]) + '%', backgroundColor: zdfbBarColor(idx) }"></div>
                    </div>
                    <span class="zdfb-value" :style="{ color: zdfbBarColor(idx) }">
                      {{ store.marketOverview.zdfb[idx] ?? 0 }}
                      <template v-if="store.marketPrevious">
                        <span v-if="zdfbDiff(idx) > 0" class="zdfb-arrow" :class="'arrow-up'">▲</span>
                        <span v-else-if="zdfbDiff(idx) < 0" class="zdfb-arrow" :class="'arrow-down'">▼</span>
                      </template>
                    </span>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>
          <el-empty v-else description="点击刷新数据加载市场概况" />
        </div>
      </el-tab-pane>

      <!-- 两融-主力数据 -->
      <el-tab-pane label="两融-主力数据" name="margin">
        <div class="margin-panel">
          <el-form inline class="search-form">
            <el-form-item label="股票代码">
              <el-input v-model="store.searchCode" placeholder="请输入股票代码" style="width: 160px;" @keyup.enter="loadMarginData" />
            </el-form-item>
            <el-form-item label="查询日期">
              <el-date-picker v-model="store.searchDate" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 160px;" />
            </el-form-item>
            <el-form-item label="Cookie">
              <el-input v-model="store.majorCookie" placeholder="主力资金查询cookie" style="width: 200px;" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadMarginData" :loading="loading">查询</el-button>
            </el-form-item>
          </el-form>

          <el-card v-if="store.marginData" shadow="hover">
            <template #header>
              <div class="card-header">
                <span>{{ store.marginData.name }} ({{ store.marginData.code }}) - {{ store.marginData.tradeDate }}</span>
              </div>
            </template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="代码">{{ store.marginData.code }}</el-descriptions-item>
              <el-descriptions-item label="股票名称">{{ store.marginData.name }}</el-descriptions-item>
              <el-descriptions-item label="日期">{{ store.marginData.tradeDate }}</el-descriptions-item>
              <el-descriptions-item label="收盘价">{{ store.marginData.closePrice }}</el-descriptions-item>
              <el-descriptions-item label="涨跌幅">{{ store.marginData.changeRate }}%</el-descriptions-item>
              <el-descriptions-item label="主力净流入-净额">{{ store.marginData.majorFlow }}</el-descriptions-item>
              <el-descriptions-item label="超大单净流入-净额">{{ store.marginData.extraLargeFlow }}</el-descriptions-item>
              <el-descriptions-item label="大单净流入-净额">{{ store.marginData.largeFlow }}</el-descriptions-item>
              <el-descriptions-item label="融资净买入">{{ store.marginData.marginNetBuy }}</el-descriptions-item>
              <el-descriptions-item label="判断标签">
                <el-tag :color="getTagColor(store.marginData.tag)" effect="dark">{{ store.marginData.tag }}</el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
          <el-empty v-else-if="!loading" description="请输入股票代码后查询" />

          <!-- 查询历史记录 -->
          <el-card v-if="store.marginHistory.length" class="history-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span>查询历史</span>
                <el-button type="danger" link size="small" @click="clearHistory">清空</el-button>
              </div>
            </template>
            <el-table :data="store.marginHistory" stripe border size="small" style="width: 100%">
              <el-table-column prop="tradeDate" label="日期" width="110" />
              <el-table-column prop="code" label="代码" width="90" />
              <el-table-column prop="name" label="名称" width="100" />
              <el-table-column prop="changeRate" label="涨跌幅" width="90">
                <template #default="{ row }">
                  <span :class="changeClass(row.changeRate)">{{ row.changeRate }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="majorFlow" label="主力净流入-净额" width="140" />
              <el-table-column prop="extraLargeFlow" label="超大单净流入-净额" width="160" />
              <el-table-column prop="largeFlow" label="大单净流入-净额" width="140" />
              <el-table-column prop="marginNetBuy" label="融资净买入" width="120" />
              <el-table-column prop="tag" label="标签" width="90">
                <template #default="{ row }">
                  <el-tag size="small" :color="getTagColor(row.tag)" effect="dark">{{ row.tag }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" fixed="right">
                <template #default="{ row }">
                  <el-button
                    v-if="store.savedRowCodes.includes(row.code)"
                    type="info" link size="small" disabled
                  >已入库</el-button>
                  <el-button
                    v-else
                    type="success" link size="small"
                    :loading="savingRow === row.code"
                    @click="handleSaveToStockM(row)"
                  >入库</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { until_test, getMarketOverview } from '@/api/untils';
import { saveToStockM } from '@/api/stock_m';
import { useDashboardStore } from '@/stores/dashboard';
import { ElMessage } from 'element-plus';

const store = useDashboardStore();

const loading = ref(false);
const savingRow = ref<string | null>(null);

/** 查询两融数据 */
async function loadMarginData() {
  loading.value = true;
  try {
    const res = await until_test({
      code: store.searchCode,
      code_date: store.searchDate || undefined,
      major_cookie: store.majorCookie || undefined,
    });
    const data = res.data.data;
    const margin = data.margin_flow as any;
    const major = data.major_flow as any;

    store.marginData = {
      code: margin['代码'] ?? major['代码'] ?? '-',
      name: margin['股票名称'] ?? major['股票名称'] ?? '-',
      tradeDate: margin['交易时间'] ?? margin['日期'] ?? major['日期'] ?? '-',
      closePrice: major['收盘价'] ?? '-',
      changeRate: major['涨跌幅'] != null ? `${major['涨跌幅']}` : '-',
      majorFlow: major['主力净流入-净额'] ?? '-',
      extraLargeFlow: major['超大单净流入-净额'] ?? '-',
      largeFlow: major['大单净流入-净额'] ?? '-',
      marginNetBuy: margin['融资净买入'] ?? '-',
      tag: data.tag ?? '-',
    };
    // 追加到历史记录（去重：同 code + tradeDate 只保留最新一条）
    const md = store.marginData!;
    const existingIdx = store.marginHistory.findIndex(
      (item) => item.code === md.code && item.tradeDate === md.tradeDate
    );
    if (existingIdx !== -1) {
      store.marginHistory.splice(existingIdx, 1);
    }
    store.marginHistory.unshift(md);
  } catch {
    store.marginData = null;
  } finally {
    loading.value = false;
  }
}

/** 涨跌幅着色 */
function changeClass(val: string) {
  if (!val) return '';
  const num = parseFloat(val);
  if (num > 0) return 'up';
  if (num < 0) return 'down';
  return '';
}

/** 查询历史记录入库 */
async function handleSaveToStockM(row: any) {
  savingRow.value = row.code;
  try {
    await saveToStockM({
      code_date: row.tradeDate,
      code: row.code,
      name: row.name,
      change_rate: row.changeRate,
      major_flow: row.majorFlow,
      extra_large_flow: row.extraLargeFlow,
      large_flow: row.largeFlow,
      rq_margin_trading: row.marginNetBuy,
      flag: row.tag,
      code_type: '其他',
    });
    ElMessage.success('已入库');
    if (!store.savedRowCodes.includes(row.code)) {
      store.savedRowCodes.push(row.code);
    }
  } catch {
    // 已由拦截器处理
  } finally {
    savingRow.value = null;
  }
}

/** 清空查询历史 */
function clearHistory() {
  store.marginHistory = [];
  store.savedRowCodes = [];
}

function getTagColor(tag: string) {
  if (tag.startsWith('好')) return '#f56c6c';
  if (tag.startsWith('差')) return '#67c23a';
  if (tag === '中+') return '#d68910';
  if (tag.startsWith('中')) return '#e6a23c';
  return '#909399';
}

/** 涨跌停统计项 */
const zdtItems = [
  { label: '涨停家数', key: 'ztzs' as const, cls: 'up' },
  { label: '跌停家数', key: 'dtzs' as const, cls: 'down' },
  { label: '上涨家数', key: 'znum' as const, cls: 'up' },
  { label: '下跌家数', key: 'dnum' as const, cls: 'down' },
];

/** 涨跌幅分布区间标签 */
const zdfbLabels = [
  { label: '-8%~-跌停' },
  { label: '-6%~-8%' },
  { label: '-4%~-6%' },
  { label: '-2%~-4%' },
  { label: '0%~-2%' },
  { label: '0%~2%' },
  { label: '2%~4%' },
  { label: '4%~6%' },
  { label: '6%~8%' },
  { label: '8%~涨停' },
];

/** 获取市场概况 */
async function loadMarketOverview() {
  store.marketLoading = true;
  try {
    const res = await getMarketOverview();
    const d = res.data.data;
    // 保存上一次数据用于对比（深拷贝，避免zdfb数组引用相同）
    store.marketPrevious = store.marketOverview
      ? {
          ztzs: store.marketOverview.ztzs,
          dtzs: store.marketOverview.dtzs,
          znum: store.marketOverview.znum,
          dnum: store.marketOverview.dnum,
          zdfb: [...store.marketOverview.zdfb],
        }
      : null;
    store.marketOverview = {
      ztzs: d.zdt_data.ztzs,
      dtzs: d.zdt_data.dtzs,
      znum: d.zdt_data.znum ?? 0,
      dnum: d.zdt_data.dnum ?? 0,
      zdfb: d.zdfb_data,
    };
    store.marketSuggestion = d.suggestion ?? '';
  } catch {
    // 已由拦截器处理
  } finally {
    store.marketLoading = false;
  }
}

/** 涨跌幅分布标签着色 */
function zdfbLabelClass(idx: number) {
  if (idx <= 4) return 'down';
  return 'up';
}

/** 进度条百分比（相对于最大值） */
function zdfbPercentage(val: number | undefined) {
  if (val == null || val === 0) return 0;
  const arr = store.marketOverview?.zdfb ?? [1];
  const max = Math.max(...arr);
  if (max === 0) return 0;
  const pct = Math.round((val / max) * 100);
  return Math.max(pct, 5);
}

/** 进度条颜色：下跌绿色，上涨红色 */
function zdfbBarColor(idx: number) {
  if (idx <= 4) return '#67c23a';
  return '#f56c6c';
}

/** 两次刷新之间的差值 */
function zdfbDiff(idx: number) {
  if (!store.marketPrevious) return 0;
  const curr = store.marketOverview!.zdfb[idx] ?? 0;
  const prev = store.marketPrevious.zdfb[idx] ?? 0;
  return curr - prev;
}
</script>

<style scoped>
.data-analysis {
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

.history-card {
  margin-top: 16px;
}

.market-panel {
  padding: 10px 0;
}

.market-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.market-suggestion {
  font-size: 22px;
  font-weight: 600;
  color: #f56c6c;
}

.stat-item {
  text-align: center;
}

.stat-label {
  color: #909399;
  font-size: 14px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 36px;
  font-weight: 600;
}

.stat-value.up {
  color: #f56c6c;
}

.stat-value.down {
  color: #67c23a;
}

.zdfb-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.zdfb-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.zdfb-label {
  width: 90px;
  text-align: right;
  font-size: 13px;
  flex-shrink: 0;
}

.zdfb-bar-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  background: #f5f7fa;
  border-radius: 4px;
  height: 20px;
  position: relative;
  overflow: hidden;
}

.zdfb-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
  min-width: 0;
}

.zdfb-value {
  width: 50px;
  text-align: right;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.zdfb-arrow {
  font-size: 10px;
  margin-left: 2px;
}

.arrow-up {
  color: #f56c6c;
}

.arrow-down {
  color: #67c23a;
}

.up {
  color: #f56c6c;
  font-weight: 600;
}

.down {
  color: #67c23a;
  font-weight: 600;
}
</style>
