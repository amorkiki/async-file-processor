import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'


export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  test: {
    globals: true,                // 直接使用 describe, it, expect 无需 import
    environment: 'jsdom',         // 模拟浏览器 DOM
    setupFiles: './src/test/setup.ts',
    css: true,                    // 处理 CSS 导入（Tailwind）
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
    },
  },
})