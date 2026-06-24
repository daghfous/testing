export const IS_DEPLOYED_WITH_PMF: boolean = [true, 'true'].includes(process.env.DEPLOYING_WITH_PMF || '')
export const RELEASE_NAME: string | undefined = process.env.RELEASE_NAME
export const ASSETS_CUSTOM_PATH: string | undefined = process.env.ASSETS_CUSTOM_PATH
export const APP_VERSION: string | undefined = process.env.APP_VERSION
export const VITE_TOP_MENU_STATIC_CONFIG: string = process.env.VITE_TOP_MENU_STATIC_CONFIG || '{}'
export const DEFAULT_ROW_PER_PAGE_VALUES: number[] = [5, 10, 25, 50, 100, 200]
