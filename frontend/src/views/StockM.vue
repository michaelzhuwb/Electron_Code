<template>
  <!-- 备选标的页面：筛选栏 + 数据表格 + 分页 -->
  <div class="stock-m-page">
    <!-- 筛选栏：选股日期 / 标签 / 股票代码 -->
    <el-card class="filter-card">
      <el-form :inline="true" class="filter-form">
        <el-form-item label="选股日期">
          <el-select v-model="store.filterCodeDate" placeholder="请选择" @change="handleFilter" style="width: 150px">
            <el-option label="最新" value="latest" />
            <el-option v-for="d in dates" :key="d" :value="d" :label="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="store.filterFlag" placeholder="全部" clearable @change="handleFilter" style="width: 150px">
            <el-option v-for="t in tags" :key="t" :value="t" :label="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="股票代码">
          <el-input v-model="store.filterCode" placeholder="输入代码" clearable @keyup.enter="handleFilter" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleFilter">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
          <el-button type="success" @click="showUploadDialog = true">导入Excel</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格：显示备选标的列表 -->
    <el-card class="table-card">
      <template #header>
        <div class="table-header-row">
          <span>备选标的</span>
          <span v-if="dashboardStore.marketSuggestion" class="market-suggestion">{{ dashboardStore.marketSuggestion }}</span>
        </div>
      </template>
      <el-table :data="tableData" v-loading="loading" stripe style="width: 100%" @sort-change="handleSort">
        <el-table-column
          prop="code_date"
          label="选股日期"
          width="120"
          sortable="custom"
        />
        <el-table-column prop="code" label="股票代码" width="120" />
        <el-table-column prop="name" label="股票名称" width="140" />
        <el-table-column prop="change_rate" label="涨跌幅" width="110">
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
        >
          <template #default="{ row }">
            <el-tag v-if="row.flag" size="small" :color="getFlagColor(row.flag)" effect="dark">{{ row.flag }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openEdit(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="store.pagination.page"
          v-model:page-size="store.pagination.size"
          :total="store.pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="showEditDialog" title="编辑备选标的" width="420px">
      <el-form label-width="70px">
        <el-form-item label="股票代码">
          <span>{{ editRow?.code }}</span>
        </el-form-item>
        <el-form-item label="股票名称">
          <span>{{ editRow?.name }}</span>
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="editFlag" placeholder="选择标签" style="width: 100%">
            <el-option v-for="t in tags" :key="t" :value="t" :label="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="形态">
          <el-select v-model="editCodeType" placeholder="选择形态" style="width: 100%">
            <el-option v-for="t in codeTypes" :key="t" :value="t" :label="t" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 上传Excel弹窗 -->
    <el-dialog v-model="showUploadDialog" title="导入Excel" width="480px">
      <el-form label-width="90px">
        <el-form-item label="选股日期">
          <el-date-picker v-model="uploadCodeDate" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" />
          <span style="margin-left: 10px; color: #909399; font-size: 12px;">留空则取上一个交易日</span>
        </el-form-item>
        <el-form-item label="Excel文件" style="width: 100%">
          <el-upload
            :auto-upload="false"
            :limit="1"
            accept=".xlsx,.xls,.csv"
            :on-change="handleFileChange"
            :file-list="fileList"
            style="width: 100%"
          >
            <el-button type="primary">选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item v-if="uploadProgress !== null">
          <el-progress :percentage="uploadProgress" :status="uploadStatus" />
          <span style="font-size: 12px; color: #909399;">{{ uploadMessage }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeUploadDialog">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="!uploadFile" @click="handleUploadExcel">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { getStockM, getStockMDates, getStockMTags, updateStockM, deleteStockM, uploadStockMExcel, getUploadTaskStatus } from '@/api/stock_m';
import type { StockMItem } from '@/api/stock_m';
import { useStockMStore } from '@/stores/stockM';
import { useDashboardStore } from '@/stores/dashboard';
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus';
import type { UploadUserFile } from 'element-plus';

const store = useStockMStore();
const dashboardStore = useDashboardStore();

const tableData = ref<StockMItem[]>([]);
const loading = ref(false);

const dates = ref<string[]>([]);
const tags = ref<string[]>([]);
const codeTypes = ['上影线', '低吸', '突破', '其他'];

// 编辑弹窗状态
const showEditDialog = ref(false);
const editRow = ref<StockMItem | null>(null);
const editFlag = ref('');
const editCodeType = ref('');
const editSaving = ref(false);

// 上传Excel弹窗状态
const showUploadDialog = ref(false);
const uploadCodeDate = ref('');
const uploading = ref(false);
const uploadFile = ref<File | null>(null);
const fileList = ref<UploadUserFile[]>([]);
const uploadProgress = ref<number | null>(null);
const uploadStatus = ref<string>('');
const uploadMessage = ref('');

/** 文件选择变化 */
function handleFileChange(file: any) {
  uploadFile.value = file.raw;
  fileList.value = [file];
  uploadProgress.value = null;
  uploadStatus.value = '';
  uploadMessage.value = '';
}

/** 关闭上传弹窗 */
function closeUploadDialog() {
  showUploadDialog.value = false;
  uploadFile.value = null;
  fileList.value = [];
  uploadProgress.value = null;
  uploadStatus.value = '';
  uploadMessage.value = '';
}

/** 导入Excel */
async function handleUploadExcel() {
  if (!uploadFile.value) return;
  uploading.value = true;
  uploadProgress.value = 0;
  uploadStatus.value = '';
  uploadMessage.value = '正在导入...';
  try {
    const res = await uploadStockMExcel(uploadFile.value, uploadCodeDate.value || undefined);
    const taskId = res.data.data.task_id;
    uploadMessage.value = '任务已启动，等待完成...';
    // 轮询任务状态
    const poll = setInterval(async () => {
      try {
        const statusRes = await getUploadTaskStatus(taskId);
        const task = statusRes.data.data;
        uploadProgress.value = task.progress ?? 0;
        if (task.status === 'done') {
          clearInterval(poll);
          uploadProgress.value = 100;
          uploadStatus.value = 'success';
          uploadMessage.value = task.result?.msg ?? '导入完成';
          ElNotification.success({ title: '导入成功', message: task.result?.msg ?? '导入完成', position: 'bottom-right' });
          uploading.value = false;
          // 刷新列表
          fetchData();
          loadDates();
          loadTags();
        } else if (task.status === 'failed') {
          clearInterval(poll);
          uploadProgress.value = 0;
          uploadStatus.value = 'exception';
          uploadMessage.value = '导入失败: ' + (task.error || '未知错误');
          ElNotification.error({ title: '导入失败', message: task.error || '未知错误', position: 'bottom-right' });
          uploading.value = false;
        }
      } catch {
        clearInterval(poll);
        uploadStatus.value = 'exception';
        uploadMessage.value = '查询任务状态失败';
        uploading.value = false;
      }
    }, 1000);
  } catch {
    uploadProgress.value = 0;
    uploadStatus.value = 'exception';
    uploadMessage.value = '启动导入任务失败';
    uploading.value = false;
  }
}

/** 涨跌幅着色：正数红色，负数绿色 */
function changeClass(val: string) {
  if (!val) return '';
  const num = parseFloat(val.replace('%', ''));
  if (num > 0) return 'up';
  if (num < 0) return 'down';
  return '';
}

/** 标签着色：好→红色，中→橙色，差→绿色 */
function getFlagColor(flag: string) {
  if (flag.startsWith('好')) return '#f56c6c';
  if (flag.startsWith('差')) return '#67c23a';
  if (flag === '中+') return '#d68910';
  if (flag.startsWith('中')) return '#e6a23c';
  return '#909399';
}

async function loadDates() {
  try {
    const res = await getStockMDates();
    dates.value = res.data.data as string[];
  } catch {}
}

async function loadTags() {
  try {
    const res = await getStockMTags();
    tags.value = res.data.data as string[];
  } catch {}
}

async function fetchData() {
  loading.value = true;
  try {
    const res = await getStockM({
      code_date: (store.filterCodeDate && store.filterCodeDate !== 'latest') ? store.filterCodeDate : undefined,
      flag: store.filterFlag || undefined,
      code: store.filterCode || undefined,
      sort_by: store.sortState.sort_by,
      sort_order: store.sortState.sort_order,
      page: store.pagination.page,
      size: store.pagination.size,
    });
    tableData.value = res.data.data.data;
    store.pagination.total = res.data.data.total;
  } catch {
    // 错误已由 axios 拦截器处理
  } finally {
    loading.value = false;
  }
}

function handleFilter() {
  store.pagination.page = 1;
  fetchData();
}

function resetFilter() {
  store.filterCodeDate = 'latest';
  store.filterFlag = null;
  store.filterCode = '';
  store.sortState = { sort_by: 'date', sort_order: 'desc' };
  store.pagination.page = 1;
  fetchData();
}

function handleSort({ prop, order }: { prop: string; order: string | null }) {
  if (!order) {
    store.sortState.sort_by = 'date';
    store.sortState.sort_order = 'desc';
  } else {
    store.sortState.sort_by = prop === 'code_date' ? 'date' : 'flag';
    store.sortState.sort_order = order === 'ascending' ? 'asc' : 'desc';
  }
  store.pagination.page = 1;
  fetchData();
}

/** 打开编辑弹窗 */
function openEdit(row: StockMItem) {
  editRow.value = row;
  editFlag.value = row.flag;
  editCodeType.value = row.code_type;
  showEditDialog.value = true;
}

/** 保存编辑 */
async function saveEdit() {
  if (!editRow.value) return;
  editSaving.value = true;
  try {
    await updateStockM({
      code_date: editRow.value.code_date,
      code: editRow.value.code,
      flag: editFlag.value,
      code_type: editCodeType.value,
    });
    // 更新本地数据
    const idx = tableData.value.findIndex(r => r.code === editRow.value?.code && r.code_date === editRow.value?.code_date);
    if (idx !== -1) {
      tableData.value[idx].flag = editFlag.value;
      tableData.value[idx].code_type = editCodeType.value;
    }
    showEditDialog.value = false;
    ElMessage.success('保存成功');
  } catch {
    // 已由拦截器处理
  } finally {
    editSaving.value = false;
  }
}

/** 删除备选标的记录 */
async function handleDelete(row: StockMItem) {
  try {
    await ElMessageBox.confirm(`确定删除 ${row.name}(${row.code})？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    });
    await deleteStockM(row.code_date, row.code);
    tableData.value = tableData.value.filter(
      (r) => !(r.code_date === row.code_date && r.code === row.code)
    );
    store.pagination.total = Math.max(0, store.pagination.total - 1);
    ElMessage.success('已删除');
    // 同步清除查询历史中的入库标记
    const idx = dashboardStore.savedRowCodes.indexOf(row.code);
    if (idx !== -1) dashboardStore.savedRowCodes.splice(idx, 1);
  } catch {
    // 用户取消或删除失败
  }
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

.table-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.market-suggestion {
  font-size: 20px;
  font-weight: 600;
  color: #f56c6c;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
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
