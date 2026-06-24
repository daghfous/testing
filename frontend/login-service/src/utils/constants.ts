import EnvService from '@ateme/cathodic-ui/src/services/EnvService.ts'

export const isStandaloneMode =
  Object.keys(JSON.parse(EnvService.getInstance().getEnv('VITE_TOP_MENU_STATIC_CONFIG') || '{}')).length > 0
