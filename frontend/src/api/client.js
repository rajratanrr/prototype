import axios from 'axios'

// Live Render Backend: https://prototype-euj7.onrender.com/api
// Uses /api in local development (proxied by Vite), and Render in production by default
const API_BASE = import.meta.env.VITE_API_URL || 
  (import.meta.env.DEV ? '/api' : 'https://prototype-euj7.onrender.com/api')

const client = axios.create({ baseURL: API_BASE })

export const apiHealth = () => client.get('/health')

export const apiStartAnalysis = (data) => client.post('/analyze', data)

export const apiGetStatus = (jobId) => client.get(`/status/${jobId}`)

export const apiGetResults = (jobId) => client.get(`/results/${jobId}`)

export const apiGetMines = () => client.get('/demo/mines')

export const apiDownload = (jobId, fmt) =>
  client.get(`/download/${jobId}/${fmt}`, { responseType: 'blob' })

export default client
