import axios from 'axios'

// In production (Netlify), VITE_API_URL should point to your deployed backend.
// e.g. https://geomines-ai.onrender.com/api
// In local dev, it falls back to '/api' which is proxied to localhost:8000 by vite.config.js
const API_BASE = import.meta.env.VITE_API_URL || '/api'

const client = axios.create({ baseURL: API_BASE })

export const apiHealth = () => client.get('/health')

export const apiStartAnalysis = (data) => client.post('/analyze', data)

export const apiGetStatus = (jobId) => client.get(`/status/${jobId}`)

export const apiGetResults = (jobId) => client.get(`/results/${jobId}`)

export const apiGetMines = () => client.get('/demo/mines')

export const apiDownload = (jobId, fmt) =>
  client.get(`/download/${jobId}/${fmt}`, { responseType: 'blob' })

export default client
