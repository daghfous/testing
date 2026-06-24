import { storeToRefs } from 'pinia'
import { createRouter, createWebHashHistory, Router, RouteRecordRaw } from 'vue-router'

import AuthStorageService from '../../services/AuthStorageService'
import CurrentUserService from '../../services/CurrentUserService'
import tokenService from '../../services/TokenService'
import { loginServiceUsersStore } from '../../users/store'
import login from '../auth'
import { afterLoginSuccessed } from '../loginInstance'
// eslint-disable-next-line
// @ts-ignore
import CreateAdmin from '../views/CreateAdmin.vue'
// eslint-disable-next-line
// @ts-ignore
import FirstLoginPage from '../views/FirstLoginPage.vue'
// eslint-disable-next-line
// @ts-ignore
import LoginPage from '../views/LoginPage.vue'
/**
 * Path reserved to login route
 */
const loginPath: string = '/login'

/**
 * Path reserved to login route
 */
export const firstLoginPath: string = '/firstLogin'

export const passwordExpirationPath: string = '/passwordExpiration'
/**
 * Path reserved to create admin login route
 */
const createAdminPath: string = '/createAdmin'

/**
 * Default verification function, test if user is logged in
 * @returns {boolean} - is the user logged
 */
const isLoggedIn = (): boolean =>
  !!tokenService.sessionToken && AuthStorageService.getFromLocalStorage('isTokenActive') === 'true'

/**
 * Default verification function, if user is trying to log in for 1st time, catch his username to display at update password page
 * @returns {object} - the current username
 */
const currentUserName = (): { username: string | null } => ({ username: CurrentUserService.getUsername() })

/**
 * Default verification function, if user is trying to log in for 1st time, catch his username to display at update password page
 * @returns {object} - the current idp name
 */
const currentUserIdpName = (): { idp_name: string | null } => ({ idp_name: CurrentUserService.getUserIdpName() })

export interface RouterOptions {
  defaultAdminLevel: number | null
}

/**
 * This function initializes the router with common logic between all apps
 * @param {string} projectName - Name of current project
 * @param {object} options - options for auth router
 * @param {string} productLoginLogo - product login pages logo
 * @returns {Router} - The router of the project
 */
export default (
  projectName: string,
  options: RouterOptions = { defaultAdminLevel: 0 },
  productLoginLogo: string
): Router => {
  const routes: unknown = [
    {
      path: loginPath,
      name: 'Login',
      component: LoginPage,
      props: () => ({
        afterLoginSuccessed: () => afterLoginSuccessed(),
        projectName,
        login: login.login,
        loginWithSaml: login.loginWithSaml,
        logUser: login.logUser,
        productLoginLogo
      })
    },
    {
      path: firstLoginPath,
      name: 'FirstLogin',
      component: FirstLoginPage,
      props: () => ({
        currentUserName: currentUserName().username,
        currentUserIdpName: currentUserIdpName().idp_name,
        projectName,
        productLoginLogo
      })
    },
    {
      path: passwordExpirationPath,
      name: 'PasswordExpiration',
      component: FirstLoginPage,
      props: () => ({
        currentUserName: currentUserName().username,
        currentUserIdpName: currentUserIdpName().idp_name,
        passwordExpiration: true,
        projectName,
        productLoginLogo
      })
    },
    {
      path: createAdminPath,
      name: 'CreateAdmin',
      component: CreateAdmin,
      props: () => ({
        projectName,
        defaultAdminLevel: options.defaultAdminLevel,
        productLoginLogo
      })
    }
  ]

  const router: Router = createRouter({
    history: createWebHashHistory(),
    routes: routes as RouteRecordRaw[]
  })

  /**
   * Callbacks used to execute custom before navigation guards for hash based routes defined in route meta property
   */
  router.beforeEach(async (to, from, next) => {
    const store = loginServiceUsersStore()
    const { isAlreadyAnAdmin } = store
    const { getFirstUser } = storeToRefs(store)
    // Test if adminExist item exist, if not create one to set redirection
    await isAlreadyAnAdmin()
    const isAnAdmin = (): boolean => {
      return !getFirstUser.value
    }
    if (!isAnAdmin()) {
      if (to.path !== createAdminPath) {
        // Redirect to Create admin page
        next({ path: createAdminPath })
      } else {
        next()
      }
    } else if (CurrentUserService.isFirstLogin() && isLoggedIn() && isAnAdmin()) {
      // If logged, but it's first login
      if (to.path !== firstLoginPath) {
        // Redirect to firstLoginPage
        next({ path: firstLoginPath })
      } else {
        next()
      }
    } else if (CurrentUserService.isPasswordExpired() && isLoggedIn() && isAnAdmin()) {
      // If logged, but it's first login
      if (to.path !== passwordExpirationPath) {
        // Redirect to firstLoginPage
        next({ path: passwordExpirationPath })
      } else {
        next()
      }
    } else if (!isLoggedIn() && isAnAdmin()) {
      // Prevent login dead-looping
      if (to.path !== loginPath) {
        // Redirect to login
        next({ path: loginPath })
      } else {
        next()
      }
    } else {
      if (to.path !== '/') {
        if (!isLoggedIn()) {
          afterLoginSuccessed()
        }
      }
      next()
    }
  })

  return router
}
