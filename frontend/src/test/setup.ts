import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'

// URL 模拟：保留构造函数，只添加静态方法
if (typeof window.URL !== 'undefined') {
  // 如果 URL.createObjectURL 不存在，添加它
  if (!window.URL.createObjectURL) {
    Object.defineProperty(window.URL, 'createObjectURL', {
      value: vi.fn(() => 'blob:mock-url'),
      configurable: true,
      writable: true,
    })
  }
  if (!window.URL.revokeObjectURL) {
    Object.defineProperty(window.URL, 'revokeObjectURL', {
      value: vi.fn(),
      configurable: true,
      writable: true,
    })
  }
} else {
  // 极少数情况 jsdom 未提供 URL，则创建一个完整 mock
  ; (window as any).URL = class URL {
    constructor(url: string, base?: string) { }
    static createObjectURL = vi.fn(() => 'blob:mock-url')
    static revokeObjectURL = vi.fn()
  }
}

// 模拟 matchMedia（Shadcn 需要）
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// 删除可能存在的旧定义（避免冲突）
delete (window as any).ResizeObserver;

// 使用 class 定义可构造的 ResizeObserver
window.ResizeObserver = class ResizeObserver {
  constructor() {
    // 空构造函数，满足 new 调用
  }
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
} as any;

// 全局清理
afterEach(() => {
  vi.clearAllMocks()
})