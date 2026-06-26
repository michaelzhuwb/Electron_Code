import request from './request';

export const until_test = (params:{
  code?:string,
  code_date?:string
}) => {
  return request.get('/untils/get_code_margin',{ params });
};

export const getMarketOverview = () => {
  return request.get('/untils/market_overview');
};
