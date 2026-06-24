/**
 * Axios 实例及全局拦截器配置
 * - 所有 API 请求会经过此实例发出
 * - 响应拦截器统一处理错误提示和错误抛出
 */
import axios from 'axios';
import { ElMessage } from 'element-plus';
import type { ApiResponse } from '@/types';

const request = axios.create({
  // 开发环境：/api 代理到 http://127.0.0.1:18000
  // 生产环境：Electron 直接请求 127.0.0.1:18000
  baseURL: import.meta.env.DEV ? '/api' : 'http://127.0.0.1:18000/api',
  timeout: 60000,  // 聊天接口需要更长的超时时间
});

// 响应拦截器：统一处理错误提示
request.interceptors.response.use(
  (response) => {
    const data: ApiResponse<any> = response.data;
    // 如果业务 code 不是 200，说明后端主动返回了错误
    if (data.code !== 200) {
      ElMessage.error(data.msg || '请求失败');
      return Promise.reject(new Error(data.msg));
    }
    return response;
  },
  (error) => {
    // HTTP 请求层面的错误（如网络不通、超时）
    ElMessage.error(error.message || '网络错误');
    return Promise.reject(error);
  }
);

export default request;
