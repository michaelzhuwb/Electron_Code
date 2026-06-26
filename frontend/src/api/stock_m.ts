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

/**
 * 上传 Excel 批量导入备选标的（异步，返回 task_id）
 * @param file Excel 文件
 * @param codeDate 选股日期，空则用当天
 */
export const uploadStockMExcel = (file: File, codeDate?: string) => {
  const formData = new FormData();
  formData.append('file', file);
  const params: Record<string, string> = {};
  if (codeDate) params.code_date = codeDate;
  return request.post('/stock-m/upload', formData, {
    params,
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

/**
 * 查询导入任务状态
 */
export const getUploadTaskStatus = (taskId: string) => {
  return request.get(`/stock-m/task/${taskId}`);
};

/**
 * 更新备选标的的标签/形态
 */
export const updateStockM = (params: {
  code_date: string;
  code: string;
  flag?: string;
  code_type?: string;
}) => {
  return request.patch('/stock-m/update', null, { params });
};

/**
 * 保存单条查询记录到备选标的
 */
export const saveToStockM = (params: {
  code_date: string;
  code: string;
  name?: string;
  change_rate?: string;
  major_flow?: string;
  extra_large_flow?: string;
  large_flow?: string;
  rq_margin_trading?: string;
  flag?: string;
  code_type?: string;
}) => {
  return request.post('/stock-m/save', null, { params });
};

/**
 * 删除备选标的记录
 */
export const deleteStockM = (code_date: string, code: string) => {
  return request.delete(`/stock-m/${code_date}/${code}`);
};
