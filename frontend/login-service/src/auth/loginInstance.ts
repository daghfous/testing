// Initialize EnvService before any other imports that might use getEnv()
import './initEnv'

import { App } from 'vue'
import { createPinia, Pinia, storeToRefs } from 'pinia'
import { Router } from 'vue-router'

import { i18n, keyEnUs } from '@ateme/cathodic-ui/src/services/I18nNext'
import vueUtils from '@ateme/cathodic-ui/src/utils/vueUtils'
import EnvService from '@ateme/cathodic-ui/src/services/EnvService.ts'

import routerDefinition, { RouterOptions } from './router'
import { authStore } from './store'
import langMessages from '../lang'
import AuthStorageService from '../services/AuthStorageService'
import CurrentUserService from '../services/CurrentUserService'
import tokenService from '../services/TokenService'
import Logger from '@ateme/cathodic-ui/src/services/Logger.ts'
import { getTrueBasePath } from '../utils/Urls.ts'

export const useAuth = () => {
  const store = authStore()
  const { projectInitialize } = storeToRefs(store)
  const { setProjectInitialize, getProjectInitialize } = store
  return { projectInitialize, setProjectInitialize, getProjectInitialize }
}

export interface IAppOptions {
  app: App
  projectName: string
  productLoginLogo: string
  langLocale?: string
  optionsLogin: RouterOptions
  useLegacyI18N?: boolean
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  projectInitialize?: any
}

export default class InitializeLogin {
  private app: App
  private store: Pinia | undefined
  private router: Router | undefined
  private name: string | undefined

  constructor() {
    this.app = {} as App
    this.store = undefined
    this.router = undefined
    this.name = undefined
  }

  start(app: IAppOptions) {
    // Ensure EnvService is initialized before creating the view
    return EnvService.getInstance().initConfigMap().then(() => {
      return this.createView(app)
    })
  }

  /**
   * Method to setup the application
   * @param {object} options the options to use
   * @param {string} options.projectName Project name
   * @param {string} options.projectInitialize Project initialize function
   * @param {string} options.productLoginLogo Product login pages logo
   * @param {string} [options.langLocale] Optional local lang to use
   * @param {object} [options.optionsLogin] Optional options to give to router
   * @param {string} [options.optionsLogin.defaultAdminLevel] Default admin level to pass in routes
   * @returns {App | undefined} The mounted Vue app
   */
  setupApp(options: IAppOptions) {
    const { langLocale, optionsLogin, productLoginLogo, projectName, projectInitialize } = options

    document.title = `${projectName} - login`

    const router = routerDefinition(projectName, optionsLogin, productLoginLogo)

    this.app.use(router)
    i18n(this.app, {
      langMessages: langMessages,
      langLocale: (langLocale as string) || keyEnUs
    })

    const store = createPinia()
    this.app.use(store)
    this.store = store
    this.router = router
    useAuth().setProjectInitialize(projectInitialize)

    if (this.app?.mount) {
      this.app?.mount('.appLogin')
      return this.app
    }

    return undefined
  }

  createView(options: IAppOptions) {
    const sessionToken = tokenService.sessionToken

    if (sessionToken) {
      AuthStorageService.writeAuthDataInSessionStorage()
    }

    const firstLogin = CurrentUserService.isFirstLogin()
    const passwordExpired = CurrentUserService.isPasswordExpired()

    if (!sessionToken || firstLogin || passwordExpired) {
      this.app = vueUtils.createVueApp()
      return this.setupApp(options)
    } else {
      return options.projectInitialize()
    }
  }

  unmount() {
    if (this.app && this.app.unmount) {
      this.app.unmount()
    }
  }
}

export const afterLoginSuccessed = (): unknown => {
  const { getProjectInitialize } = useAuth()
  const topMenuManifestPath = EnvService.getInstance().getEnv('VITE_TOP_MENU_MANIFEST_PATH')

  if (topMenuManifestPath) {
    const url = defaultRedirectPath()

    // Store URL for main.ts to redirect AFTER app mounts (prevents blank page)
    try {
      sessionStorage.setItem('_loginRedirectUrl', url as string)
    } catch (err) {
      Logger.error('loginInstance > ', `failed to store redirect URL: ${url}`)
    }
  }

  const canInitialize = typeof getProjectInitialize === 'function'

  // Let projectInitialize() handle the app setup and redirect
  return canInitialize ? getProjectInitialize() : false
}

export const defaultRedirectPath = (): string | undefined => {
  const isValidUrl = (value: string): boolean => {
    try {
      new URL(value)
      return true
    } catch {
      return false
    }
  }

  const basePath = getTrueBasePath()

  if (!basePath) {
    return location.pathname
  }

  const lastVisitedUrl = sessionStorage.getItem('lastVisitedUrl')

  let fullLastVisitedUrl
  if (lastVisitedUrl) {
    fullLastVisitedUrl =
      lastVisitedUrl.includes(`${basePath}`) || isValidUrl(lastVisitedUrl)
        ? lastVisitedUrl
        : `/${basePath}${lastVisitedUrl}`
  }

  const preferences: string = localStorage.getItem('preferences') as string

  const favoriteApp = preferences !== 'undefined' ? JSON.parse(preferences)?.favorite_application : undefined

  const newURL = favoriteApp ? `/${basePath}/applications/${favoriteApp}` : undefined

  Logger.debug('login-service loginInstance.ts > defaultRedirectPath', 'fullLastVisitedUrl is ' + fullLastVisitedUrl)
  Logger.debug('login-service loginInstance.ts > defaultRedirectPath', 'newURL is ' + newURL)
  const redirectingTo = fullLastVisitedUrl ?? newURL ?? `/${basePath}`
  Logger.debug('login-service loginInstance.ts > defaultRedirectPath', 'so defaultRedirectPath is ' + redirectingTo)
  return redirectingTo
}
