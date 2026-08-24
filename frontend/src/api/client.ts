import axios from "axios";
import { toast } from 'sonner';

// 创建 axios 实例，统一配置
const client = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  timeout: 1000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器（可扩展：加 token、日志等）
client.interceptors.request.use(
  (config) => {
    // 例如：config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
)

// 响应拦截器（统一处理错误格式）
client.interceptors.response.use(
  (response) => response,
  (error) => {
    // 后端返回 { code, message } 或 422 的 detail (将错误信息统一成我们需要的格式)
    if (error.response) {
      const data = error.response.data;
      if (data.message) {
        error.message = data.message;
      } else if (data.detail) {
        // 422 格式：{ detail: [ { loc, msg } ] }
        error.message = data.detail.map((d: any) => d.msg).join('；')
      }
    } else if (error.request) {
      error.message = '网络连接失败，请检查后端服务是否启动';
    }
    // 网络错误或超时
    toast.error(error.message);
    return Promise.reject(error);
  })

export default client;