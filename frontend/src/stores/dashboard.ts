// 首页仪表盘状态管理：页签、查询条件、两融数据、市场概况
import { defineStore } from 'pinia';
import { ref, watch, toRaw } from 'vue';

export interface MarginData {
  code: string;
  name: string;
  tradeDate: string;
  closePrice: string;
  changeRate: string;
  majorFlow: string;
  extraLargeFlow: string;
  largeFlow: string;
  marginNetBuy: string;
  tag: string;
}

export interface MarketOverview {
  ztzs: number;
  dtzs: number;
  znum: number;
  dnum: number;
  zdfb: number[];
}

export const useDashboardStore = defineStore('dashboard', () => {
  // 当前激活的页签（首页 / 两融数据 / 市场概况）
  const activeTab = ref('welcome');

  // 股票代码查询条件
  const searchCode = ref('002049');

  // 查询日期
  const searchDate = ref('');

  // 两融数据
  const marginData = ref<MarginData | null>(null);

  // 两融查询历史记录（localStorage 持久化）
  const _loadMarginHistory = (): MarginData[] => {
    const raw = localStorage.getItem('marginHistory');
    return raw ? JSON.parse(raw) : [];
  };
  const marginHistory = ref<MarginData[]>(_loadMarginHistory());
  watch(marginHistory, (val) => {
    localStorage.setItem('marginHistory', JSON.stringify(toRaw(val)));
  }, { deep: true });

  // 已入库的股票代码列表（localStorage 持久化）
  const savedRowCodes = ref<string[]>(
    JSON.parse(localStorage.getItem('savedRowCodes') || '[]')
  );
  watch(savedRowCodes, (val) => {
    localStorage.setItem('savedRowCodes', JSON.stringify(val));
  }, { deep: true });

  // 市场概况
  const _loadMarketOverview = (): MarketOverview | null => {
    const raw = localStorage.getItem('marketOverview');
    return raw ? JSON.parse(raw) : null;
  };
  const marketOverview = ref<MarketOverview | null>(_loadMarketOverview());
  const marketPrevious = ref<MarketOverview | null>(null);
  const marketLoading = ref(false);
  watch(marketOverview, (val) => {
    if (val) localStorage.setItem('marketOverview', JSON.stringify(toRaw(val)));
  }, { deep: true });

  // 策略建议（localStorage 持久化，刷新后仍保留）
  const marketSuggestion = ref(localStorage.getItem('marketSuggestion') || '');
  watch(marketSuggestion, (val) => {
    localStorage.setItem('marketSuggestion', val || '');
  });

  return {
    activeTab,
    searchCode,
    searchDate,
    marginData,
    marginHistory,
    savedRowCodes,
    marketOverview,
    marketPrevious,
    marketLoading,
    marketSuggestion,
  };
});
