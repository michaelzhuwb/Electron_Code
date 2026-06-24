/**
 * 股票相关 API
 */
import request from './request';

// GET /api/stocks - 获取股票列表（分页+模糊搜索）
export const getStocks = (params: { code?: string; name?: string; page: number; size: number }) => {
  return request.get('/stocks', { params });
};

// GET /api/stocks/stats - 获取涨跌统计数据
export const getStockStats = () => {
  return request.get('/stocks/stats');
};
