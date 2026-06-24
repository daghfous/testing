import { getEnv } from '@ateme/cathodic-ui/src/utils/EnvUtils';

export const IS_DEPLOYED_WITH_PMF: boolean = [true, 'true'].includes(getEnv('DEPLOYING_WITH_PMF') || '')
export const RELEASE_NAME: string | undefined = getEnv('RELEASE_NAME')
export const ASSETS_CUSTOM_PATH: string | undefined = getEnv('ASSETS_CUSTOM_PATH')
export const APP_VERSION: string | undefined = getEnv('APP_VERSION')
export const VITE_TOP_MENU_STATIC_CONFIG: string = getEnv('VITE_TOP_MENU_STATIC_CONFIG') || '{}'
export const DEFAULT_ROW_PER_PAGE_VALUES: number[] = [5, 10, 25, 50, 100, 200]
