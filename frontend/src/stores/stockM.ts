// 备选标的页面状态管理：筛选、分页、排序
import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useStockMStore = defineStore('stockM', () => {
  // 筛选条件
  const filterCodeDate = ref('latest');
  const filterFlag = ref<string | null>(null);
  const filterCode = ref('');

  // 排序状态
  const sortState = ref({
    sort_by: 'date',
    sort_order: 'desc',
  });

  // 分页参数
  const pagination = ref({ page: 1, size: 20, total: 0 });

  return {
    filterCodeDate,
    filterFlag,
    filterCode,
    sortState,
    pagination,
  };
});
