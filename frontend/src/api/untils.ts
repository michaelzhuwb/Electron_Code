import request from './request';

export const until_test = (params:{
  code?:string,
  code_date?:string,
  major_cookie?:string,
  source?:string
}) => {
  return request.get('/untils/get_code_margin',{ params });
};

export const getMarketOverview = () => {
  return request.get('/untils/market_overview');
};

export const getMarketOverviewHistory = (params?: {
  date?: string;
  page?: number;
  size?: number;
}) => {
  return request.get('/untils/market_overview_history', { params });
};
