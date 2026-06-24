/** 全局类型定义 */

/** API 统一响应包装器 */
export interface ApiResponse<T> {
  code: number;
  data: T;
  msg: string;
}

/** 分页数据结构 */
export interface PageData<T> {
  total: number;
  page: number;
  size: number;
  data: T[];
}

/** Stock 模型（股票实时行情） */
export interface StockItem {
  id: number;
  code: string;
  name: string;
  price: number;
  change_rate: number;
  volume: number;
  turnover: number;
  high: number;
  low: number;
  update_time: string;
}

/** 股票统计数据 */
export interface StockStats {
  total: number;    // 股票总数
  rising: number;   // 上涨数量
  falling: number;  // 下跌数量
  avgChange: number;  // 平均涨跌幅
}
