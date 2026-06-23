// input: axios, VITE_API_URL 环境变量(留空 → 相对路径走 Vite /api 代理)
// output: apiClient —— axios 实例(baseURL=${VITE_API_URL}/api/v1, withCredentials)
// owner: wanhua.gu
// pos: 跨域基础设施 - HTTP 客户端(后端 /api/v1 接口的统一入口)；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
import axios from 'axios'

// VITE_API_URL 留空时 baseURL 为相对路径 `/api/v1`，由 Vite dev 代理转发到后端，避免 CORS。
// 设置为绝对地址(如 http://localhost:8000)时则直连后端。
const baseURL = `${import.meta.env.VITE_API_URL ?? ''}/api/v1`

export const apiClient = axios.create({
  baseURL,
  withCredentials: true,
})
