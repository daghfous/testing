import axios from 'axios'
import { notificationStore } from '@ateme/cathodic-ui/src/components/notifications/notificationStore'
import EnvService from '@ateme/cathodic-ui/src/services/EnvService.ts'

import { LOGIN_TIMEOUT } from '../config/api'
import { IUser } from '../interfaces/Interfaces'
import AuthStorageService from '../services/AuthStorageService'
import tokenService from '../services/TokenService'
import Logger from '@ateme/cathodic-ui/src/services/Logger.ts'
import { isStandaloneMode } from '../utils/constants.ts'
import { getTrueBasePath } from '../utils/Urls.ts'
const getRootPath: string = EnvService.getInstance().getEnv('USER_MANAGEMENT_URL') || '/'

const AuthService = {
  login: async (user: IUser, afterLoginSuccessed: () => void): Promise<void> => {
    await new Promise((resolve, reject) => {
      axios({
        method: 'POST',
        url: `${getRootPath}token`,
        headers: {
          'Content-Type': 'application/json'
        },
        data: {
          username: user.login,
          password: user.password,
          idp_name: user.idp_name
        },
        timeout: LOGIN_TIMEOUT
      })
        .then(resp => {
          const sessionToken = resp.data.access_token

          if (!sessionToken) {
            AuthStorageService.clearAuthAndUserDataFromStorages()
            reject()
          }

          tokenService.sessionToken = sessionToken
          axios.defaults.headers.common['Authorization'] = tokenService.sessionToken
          if (resp.status === 200) {
            tokenService.refreshToken = resp.data.refresh_token
            AuthStorageService.addToStorages('currentUserName', user.login as string)
            AuthStorageService.addToLocalStorage('loginMode', user.mode as string)
            AuthStorageService.addToLocalStorage('ldapDomain', user.domain as string)
            AuthStorageService.addToLocalStorage('lastIdpSelected', user.idp_name as string)
            afterLoginSuccessed()
          } else if (resp.status === 206) {
            AuthStorageService.addToStorages('currentUserName', user.login as string)
            afterLoginSuccessed()
          }
          resolve(resp)
        })
        .catch(err => {
          AuthStorageService.clearAuthAndUserDataFromStorages()
          reject(err)
        })
    })
  },

  loginWithSaml: (data: IUser) => {
    const relayState = `${window.location.origin}/${getTrueBasePath()}`
    AuthStorageService.addToLocalStorage('lastIdpSelected', data.idp_name as string)
    window.location.href = `${getRootPath}idp_sso/${data.idp_name}?relay_state=${relayState}`
  },

  logUser: async (
    sessionToken: string,
    refreshToken: string,
    username: string,
    afterLoginSuccessed: () => void
  ): Promise<void> => {
    try {
      axios.defaults.headers.common['Authorization'] = sessionToken
      tokenService.sessionToken = sessionToken
      tokenService.refreshToken = refreshToken
      AuthStorageService.addToStorages('currentUserName', username)
      AuthStorageService.addToLocalStorage('loginMode', 'saml')
      AuthStorageService.addToLocalStorage('ldapDomain', '')
      AuthStorageService.deleteCookies(['access_token', 'expires_in', 'username', 'token_type', 'refresh_token'])
      afterLoginSuccessed()
    } catch (error) {
      const { notifyError } = notificationStore()
      AuthStorageService.clearAuthAndUserDataFromStorages()
      notifyError('User is not correct', '')
    }
  },

  /**
   * Builds the logout URL with the appropriate relay state.
   * @returns {string} - The constructed logout URL
   */
  buildLogoutUrl: (): string => {
    const baseURL = EnvService.getInstance().getEnv('USER_MANAGEMENT_URL')!
    const relayState = `${window.location.origin}/${getTrueBasePath()}`
    Logger.debug('login-service auth.ts > login', 'Relay state is ' + relayState)
    const url = new URL('logout', window.location.origin + baseURL)
    url.searchParams.append('relay_state', relayState)
    return url.toString()
  },

  /**
   * Logs out the current user by calling the logout API endpoint.
   * Clears authentication data from storage and redirects appropriately.
   * @param {string} [redirectPath] - Optional path to redirect to after logout
   * @param {boolean} [showAlert] - Whether to show an alert on session expiration
   */
  logout: async (redirectPath: string = '', showAlert: boolean = false) => {
    // Always add a / and only one behind the path
    const baseUrl = `${(redirectPath || getTrueBasePath() || '').replace(/\/+$/, '')}/`

    const redirectTo = (path?: string) => {
      Logger.debug(
        'login-service auth.ts > logout > redirectTo',
        `window.__envConfig.VITE_TOP_MENU_STATIC_CONFIG = ${(window as any).__envConfig?.VITE_TOP_MENU_STATIC_CONFIG}`
      )
      if (isStandaloneMode) {
        Logger.debug('login-service auth.ts > logout > redirectTo', 'We are in appliance mode')
      } else {
        Logger.debug('login-service auth.ts > logout > redirectTo', 'We are in pmf mode')
      }
      tokenService.setLastVisitedUrl()
      // Always redirect to user-management after logout to avoid landing on base path
      const targetPath = path || `${baseUrl}/user-management/`
      if (targetPath) {
        Logger.debug('login-service auth.ts > logout > redirectTo', `redirect to /${targetPath}`)
        location.assign(`/${targetPath}`)
      } else {
        Logger.debug('login-service auth.ts > logout > redirectTo', 'No targetPath, just reload')
        location.reload()
      }
    }

    const showSessionAlert = (showAlert: boolean): void => {
      const hasUser = !!AuthStorageService.getFromLocalStorage('currentUserName')
      if (hasUser && showAlert) {
        window.alert('Your session has expired. Please log in again.')
      }
    }

    try {
      const resp = await fetch(AuthService.buildLogoutUrl(), {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          Authorization: tokenService.sessionToken
        }
      })
      showSessionAlert(showAlert)
      AuthStorageService.clearAuthAndUserDataFromStorages()
      if (resp.ok) {
        const data = await resp.json().catch(() => ({}))
        const sloUrl = data?.slo_url
        redirectTo(sloUrl || baseUrl)
      } else {
        redirectTo(baseUrl)
      }
    } catch (error) {
      showSessionAlert(showAlert)
      AuthStorageService.clearAuthAndUserDataFromStorages()
      redirectTo(baseUrl)
    }
  }
}
export default AuthService
