/**
 * API 入口文件，集中导出所有通用接口
 */
import request from './request';

/** 健康检查接口，用于检测后端是否在线 */
export const healthCheck = () => {
  return request.get('/health');
};
