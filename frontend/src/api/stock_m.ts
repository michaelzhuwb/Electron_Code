/**
 * 备选标的（Stock_M）相关 API
 */
import request from './request';

export interface StockMItem {
  code_date: string;      // 选股日期
  code: string;           // 股票代码
  name: string;           // 股票名称
  change_rate: string;   // 涨跌幅
  rq_margin_trading: string;   // 融资净买入额
  major_flow: string;          // 主力净流入-净额
  extra_large_flow: string;   // 超大单净流入-净额
  large_flow: string;          // 大单净流入-净额
  code_type: string;            // 形态（上影线/低吸/突破/其他）
  flag: string;                 // 标签
}

/**
 * 获取备选标的列表（支持分页、筛选、排序）
 * - code_date: 空则默认取最新日期
 * - flag: 按标签筛选
 * - code: 按股票代码模糊搜索
 */
export const getStockM = (params: {
  code_date?: string;
  flag?: string;
  code?: string;
  sort_by?: string;   // 排序字段：date | flag
  sort_order?: string; // 排序方向：asc | desc
  page: number;
  size: number;
}) => {
  return request.get('/stock-m', { params });
};

// GET /api/stock-m/dates - 获取可选的选股日期列表（降序）
export const getStockMDates = () => {
  return request.get('/stock-m/dates');
};

// GET /api/stock-m/tags - 获取可选的标签列表
export const getStockMTags = () => {
  return request.get('/stock-m/tags');
};
