
import "@testing-library/jest-dom/vitest";

const storage = new Map<string, string>();

const localStorageMock: Storage = {
  get length() {
    return storage.size;
  },

  clear() {
    storage.clear();
  },

  getItem(key: string) {
    return storage.get(String(key)) ?? null;
  },

  key(index: number) {
    return Array.from(storage.keys())[index] ?? null;
  },

  removeItem(key: string) {
    storage.delete(String(key));
  },

  setItem(key: string, value: string) {
    storage.set(String(key), String(value));
  },
};

Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  writable: true,
  value: localStorageMock,
});

Object.defineProperty(window, "localStorage", {
  configurable: true,
  writable: true,
  value: localStorageMock,
});

Object.defineProperty(window, "scrollTo", {
  writable: true,
  value: () => {},
});

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
});
