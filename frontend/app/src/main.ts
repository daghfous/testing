import { Router } from 'vue-router'
import { Ability } from '@casl/ability'
import { abilitiesPlugin } from '@casl/vue'
import ApplicationService from '@ateme/cathodic-ui/src/services/ApplicationService'
import { dateTimeStore, ZONE_UTC } from '@ateme/cathodic-ui/src/store/dateTime'
import initializeLogin from '@ateme/login-service/src/auth/initializeLogin'
import { getSingletonBuilder } from '@ateme/login-service/src/services/abilities/AbilityBuilderRules'
import { initializeApiClient } from './api'
import langMessages from './lang/index'
import router from './router/index'
import { getEnv } from '@ateme/cathodic-ui/src/utils/EnvUtils'
import { defaultRedirectPath } from '@ateme/login-service/src/auth/loginInstance'
import Logger from '@ateme/cathodic-ui/src/services/Logger.ts'

const projectName = 'User Management'
const customRouter: Router = router(projectName)
let attempts = 0

/**
 * get the base path of the application.
 * Example: `/pmf/user-management/` -> `/pmf`.
 * Falls back to `/` when no segment is present.
 * @returns {string} - the app base path from the first pathname segment.
 */
const getBasePath = (): string => {
  const [firstPathToken] = window.location.pathname.split('/').filter(Boolean)
  return firstPathToken ? `/${firstPathToken}` : '/'
}

/**
 * Parses a redirect value into an absolute URL.
 * Relative values are resolved against the current origin.
 * @param {string} value - the redirect value to parse.
 * @returns {URL | null} `null` when parsing fails.
 */
const parseRedirectUrl = (value: string): URL | null => {
  try {
    return new URL(value, window.location.origin)
  } catch {
    return null
  }
}

/**
 * Returns `true` when the target URL is exactly the current location
 * (same pathname, query string and hash).
 * @param {URL} target - URL to compare with the current browser location.
 * @returns {boolean} `true` when both URLs point to the same location.
 */
const isSameLocation = (target: URL) =>
  target.pathname === window.location.pathname &&
  target.search === window.location.search &&
  target.hash === window.location.hash

/**
 * Checks whether the target points only to the application base path.
 * Trailing slashes are normalized before comparison.
 * Used to ignore redirects that do not target a real app route.
 * @param {URL} target - Redirect target to validate.
 * @returns {boolean} `true` when the target matches the app base path only.
 */
const isBaseOnlyTarget = (target: URL): boolean => {
  const normalizedTarget = target.pathname.replace(/\/+$/, '') || '/'
  const normalizedBase = getBasePath().replace(/\/+$/, '') || '/'
  return normalizedTarget === normalizedBase
}

/**
 * Returns `true` when the target URL points to the login route (`#/login`).
 * @param {URL} target - Redirect target to inspect.
 * @returns {boolean} `true` when the hash contains the login route.
 */
const isLoginTarget = (target: URL): boolean => target.hash.includes('/login')

/**
 * Performs the final redirect after login.
 * First rewrites the current history entry to a known-safe app URL,
 * then navigates to the computed target.
 * @param {URL} target - Final URL to open after login.
 * @returns {void}
 */
const redirectTo = (target: URL) => {
  const finalUrl = target.toString()
  const basePath = window.location.pathname.split('/')[1]
  // Keep a known-good entry in history so browser back from BFCache does not land on login again.
  const safeBackUrl = basePath ? `/${basePath}/user-management/` : '/user-management/'
  window.history.replaceState(null, '', safeBackUrl)
  window.location.assign(finalUrl)
}

/**
 * Initializes the project by setting up the application with necessary configurations.
 * This includes setting the timezone, mounting the abilities plugin, and configuring the router.
 * @returns {Promise<void>} A promise that resolves when the initialization is complete.
 */
const projectInitialize = () =>
  ApplicationService.startInitializeJustCathodic({
    beforeCreateView: () => {
      initializeLogin.unmount()
      initializeApiClient()
      // Handle redirect after app mount to avoid race conditions with initial rendering.
      const loginRedirectUrl = sessionStorage.getItem('_loginRedirectUrl')
      if (loginRedirectUrl) {
        const parsedRedirect = parseRedirectUrl(loginRedirectUrl)

        // Ignore unsafe/useless redirect targets (self/base/login) to prevent loops.
        if (
          !parsedRedirect ||
          isBaseOnlyTarget(parsedRedirect) ||
          isSameLocation(parsedRedirect) ||
          isLoginTarget(parsedRedirect)
        ) {
          sessionStorage.removeItem('_loginRedirectUrl')
        }

        sessionStorage.setItem('_postLoginHandled', 'true')

        setTimeout(() => {
          sessionStorage.removeItem('_loginRedirectUrl')
          if (parsedRedirect) {
            redirectTo(parsedRedirect)
          }
        }, 100)
        return
      }

      // Fallback when login redirect is absent: use top-menu default redirect if we are still on login.
      const hasTopMenuConfig = getEnv('VITE_TOP_MENU_MANIFEST_PATH') || getEnv('VITE_USER_PROFILE_MANIFEST_PATH')

      const isLoginPage = window.location.href.includes('#/login')

      if (hasTopMenuConfig && isLoginPage) {
        const fallbackUrl = defaultRedirectPath()
        const parsedFallbackUrl = fallbackUrl ? parseRedirectUrl(fallbackUrl as string) : null

        if (
          parsedFallbackUrl &&
          !isBaseOnlyTarget(parsedFallbackUrl) &&
          !isSameLocation(parsedFallbackUrl) &&
          !isLoginTarget(parsedFallbackUrl)
        ) {
          redirectTo(parsedFallbackUrl)
        }
      }
    },
    afterCreateView: () => {
      dateTimeStore().timezone(ZONE_UTC)
      ApplicationService.getApp()?.use(abilitiesPlugin, new Ability(getSingletonBuilder().getRules()), {
        useGlobalProperties: true
      })
    },
    langMessages,
    router: customRouter
  }).catch(err => {
    // Fallback: reload page to retry
    if (attempts >= 1) {
      Logger.error(
        'user-management/main.ts > projectInitialize',
        `Page could not be loaded even after a reload. Error is: ${err}`
      )
      return
    } else {
      attempts += 1
      location.reload()
    }
  })

/**
 * Starts the login initialization process with specified configurations.
 * This includes setting the language locale, login options, product logo, project name, and the project initialization function.
 */
// start() now returns a Promise that resolves when EnvService is initialized
initializeLogin.start({
  app: ApplicationService.getApp()!,
  productLoginLogo: '',
  langLocale: 'en-US',
  optionsLogin: {
    defaultAdminLevel: null
  },
  projectName,
  projectInitialize: projectInitialize
}).then(() => {
  Logger.debug('main.ts', 'Login initialization completed with EnvService initialized')
}).catch((error) => {
  Logger.error('main.ts', `Login initialization failed: ${error}`)
})
