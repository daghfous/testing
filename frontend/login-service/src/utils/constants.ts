// Use window.__envConfig to avoid async timing issues with EnvService
declare global {
  interface Window {
    __envConfig: Record<string, any>
  }
}

export const isStandaloneMode =
  Object.keys(JSON.parse((window as any).__envConfig?.VITE_TOP_MENU_STATIC_CONFIG || '{}')).length > 0
