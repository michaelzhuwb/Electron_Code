import request from './request';

export const until_test = (params:{
  code_date?:string
}) => {
  return request.get('/untils/get_code');
};
