import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

/**
 * jsdom exposes `localStorage` here as a bare object with none of the Storage
 * methods on it, so any module that reads it while being imported - `i18n/config`
 * does, to pick the initial language - throws before a single test runs.
 * Installing a working in-memory Storage keeps that failure out of the suites.
 */
function createMemoryStorage(): Storage {
  let entries: Record<string, string> = {}

  return {
    get length() {
      return Object.keys(entries).length
    },
    clear() {
      entries = {}
    },
    getItem(key: string) {
      return Object.prototype.hasOwnProperty.call(entries, key) ? entries[key] : null
    },
    key(index: number) {
      return Object.keys(entries)[index] ?? null
    },
    removeItem(key: string) {
      delete entries[key]
    },
    setItem(key: string, value: string) {
      entries[key] = String(value)
    },
  }
}

if (typeof globalThis.localStorage?.getItem !== 'function') {
  Object.defineProperty(globalThis, 'localStorage', {
    value: createMemoryStorage(),
    configurable: true,
    writable: true,
  })
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  vi.useRealTimers()
  localStorage.clear()
})
