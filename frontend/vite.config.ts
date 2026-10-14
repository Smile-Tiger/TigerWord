import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite 配置
// 开发时（npm run dev）前端跑在 5173，接口请求通过下面的 proxy 转给后端 8000，
// 这样前端代码里统一写 /api/xxx 就行，不用关心后端地址。
// 打包后（npm run build）产物在 frontend/dist，由后端的 FastAPI 直接托管，只跑一个服务。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
