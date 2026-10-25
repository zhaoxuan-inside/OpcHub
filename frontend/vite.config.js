import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';
import http from 'http';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        // OPCHUB_BACKEND_URL 允许本地开发指向非默认端口的后端实例
        target: process.env.OPCHUB_BACKEND_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
        // 使用独立 Agent，绕过系统 http_proxy 环境变量
        // 否则系统代理 (192.168.1.100:7890) 会接管本地 127.0.0.1 请求，返回 502
        agent: new http.Agent(),
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
