import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

class MemoryStorage implements Storage {
  private data = new Map<string, string>();
  get length(): number {
    return this.data.size;
  }
  clear(): void {
    this.data.clear();
  }
  getItem(key: string): string | null {
    return this.data.get(key) ?? null;
  }
  key(index: number): string | null {
    return Array.from(this.data.keys())[index] ?? null;
  }
  removeItem(key: string): void {
    this.data.delete(key);
  }
  setItem(key: string, value: string): void {
    this.data.set(key, value);
  }
}

// Node 26's built-in localStorage is gated behind a CLI flag, and happy-dom
// does not currently override it. Polyfill a deterministic in-memory store.
const memoryLocal = new MemoryStorage();
const memorySession = new MemoryStorage();
Object.defineProperty(window, 'localStorage', { value: memoryLocal, configurable: true });
Object.defineProperty(window, 'sessionStorage', { value: memorySession, configurable: true });
Object.defineProperty(globalThis, 'localStorage', { value: memoryLocal, configurable: true });
Object.defineProperty(globalThis, 'sessionStorage', { value: memorySession, configurable: true });

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});
