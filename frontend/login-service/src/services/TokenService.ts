import { notificationStore } from '@ateme/cathodic-ui/src/components/notifications/notificationStore'
import EnvService from '@ateme/cathodic-ui/src/services/EnvService.ts'
import axios, { AxiosError, AxiosResponse } from 'axios'
import ActivityService from './ActivityService'
import AuthStorageService from './AuthStorageService'
import { TIMEOUT, usersClient } from '../config/api'
import { RequestClient } from '../interfaces/Interfaces'
import Logger from '@ateme/cathodic-ui/src/services/Logger.ts'
import { getTrueBasePath } from '../utils/Urls.ts'

class TokenService {
  static #refreshTokenPromise: Promise<void> | null = null

  #initiateTokenRefresh(): Promise<void> {
    return usersClient
      .post(
        'refresh_token',
        { refresh_token: this.refreshToken },
        {
          headers: { 'Content-Type': 'application/json' },
          timeout: TIMEOUT
        }
      )
      .then(resp => {
        axios.defaults.headers.common['Authorization'] = resp.data.access_token
        this.sessionToken = resp.data.access_token
        this.refreshToken = resp.data.refresh_token
      })
      .catch(() => {
        if (!window.location.href.includes('login')) {
          this.clearStorageAndReload()
        }
      })
  }

  setLastVisitedUrl() {
    const isMandatoryAuthPage =
      location.href.includes('/login') ||
      location.href.includes('/firstLogin') ||
      location.href.includes('/passwordExpiration') ||
      location.href.includes('/createAdmin')
    if (!isMandatoryAuthPage) {
      // Extract path relative to base URL (removes base path prefix like /pmf)
      // to match format expected by pmf-portal listeners.js
      const fullPath = `${location.pathname}${location.search}${location.hash}`
      Logger.debug('login-service TokenService.ts > setLastVisitedUrl', 'fullPath is ' + fullPath)
      const basePath = getTrueBasePath()
      Logger.debug('login-service TokenService.ts > setLastVisitedUrl', 'basePath is ' + basePath)
      const pathWithoutBase = fullPath.replace(`/${basePath}`, '')
      sessionStorage.setItem('lastVisitedUrl', pathWithoutBase)
      Logger.debug('login-service TokenService.ts > setLastVisitedUrl', 'setting lastVisitedUrl to ' + pathWithoutBase)
    } else {
      Logger.debug(
        'login-service TokenService.ts > setLastVisitedUrl',
        'do not set the lastVisitedUrl because we are on a login-service page'
      )
    }
  }

  clearStorageAndReload() {
    Logger.debug('login-service TokenService.ts > clearStorageAndReload', `begin`)
    const currentLocation = location.pathname.split('/')[1]
    const baseUrl = EnvService.getInstance().getEnv('VITE_LOGIN_URL') || `/${currentLocation}`
    const showAlert = !!AuthStorageService.getFromLocalStorage('currentUserName')
    this.setLastVisitedUrl()
    AuthStorageService.clearAuthAndUserDataFromStorages()
    delete axios.defaults.headers.common['Authorization']
    if (showAlert) {
      window.alert('Your session has expired. Please log in again.')
    }
    if (baseUrl) {
      Logger.debug('login-service TokenService.ts > clearStorageAndReload', `Assigning url ${baseUrl}`)
      location.assign(baseUrl)
    } else {
      Logger.debug('login-service TokenService.ts > clearStorageAndReload', `Do not have baseUrl, just reload`)
      location.reload()
    }
  }

  async refreshTokenOrClearStorage(): Promise<void | null> {
    if (!ActivityService.isActive()) {
      this.clearStorageAndReload()
      return
    }

    if (!TokenService.#refreshTokenPromise) {
      TokenService.#refreshTokenPromise = this.#initiateTokenRefresh().finally(() => {
        TokenService.#refreshTokenPromise = null
      })
    }

    return TokenService.#refreshTokenPromise
  }

  /**
   * Handles HTTP response interception.
   * If a 401 (Unauthorized) is encountered, it attempts to refresh the token or clear the session.
   * @param {Response} response - Fetch API Response object
   * @returns {Promise<Response>} - The original response or a redirect to the login page
   */
  handleResponseInterceptor = async (response: Response): Promise<Response> => {
    if (response && response.status === 403) {
      const { notifyError } = notificationStore()
      notifyError('access forbidden', '')
    } else if (response && response.status === 401) {
      // Else if 401, user is not authorized to access the page or a resource and redirected to login page.
      await this.refreshTokenOrClearStorage()
    }
    return response
  }
  /**
   * Builder of axios interceptor error callback to define
   * @param {Promise} callback - the callback to call. errorTokenCallback by default
   * @returns {Promise} the created callback
   */
  tokenErrorInterceptorsBuilder =
    (callback: (error: AxiosError) => Promise<AxiosResponse | AxiosError>) =>
    async (error: AxiosError): Promise<Promise<AxiosError | AxiosResponse> | undefined> => {
      const { notifyError } = notificationStore()
      // If 403, user is not allowed to access the page and redirected to login page.
      if (error.response && error.response.status === 403) {
        notifyError('access forbidden', '')
        throw error
      } else if (error.response && error.response.status === 401) {
        // Else if 401, user is not authorized to access the page or a resource and redirected to login page.
        await this.refreshTokenOrClearStorage()
        return typeof callback === 'function' ? callback(error) : undefined
      }
      return Promise.reject(error)
    }

  /**
   * Create a callback
   * @param {object} client - client to use
   * @returns {Promise} promise of the request
   */
  errorTokenCallback =
    (client: RequestClient) =>
    (error: AxiosError): Promise<AxiosResponse | AxiosError> => {
      if (error.config) {
        error.config.headers['Authorization'] = this.sessionToken
        const { baseURL, url } = error.config

        if (baseURL && url && url.includes(baseURL)) {
          delete error.config.baseURL
        }

        return client.request(error.config)
      }
      return Promise.reject(error)
    }

  /**
   * Client token error interceptor
   * @param {object} client - client interceptor
   * @returns {Promise} promise of the request
   */
  static clientTokenErrorInterceptor = (client: RequestClient) =>
    tokenService.tokenErrorInterceptorsBuilder(tokenService.errorTokenCallback(client))

  static get bearerScheme(): string {
    return 'Bearer'
  }

  getBearerToken(token: string): string {
    if (!token || token.includes(TokenService.bearerScheme)) return token
    return `${TokenService.bearerScheme} ${token}`
  }

  // Getter and Setter for sessionToken
  get sessionToken(): string {
    const token = AuthStorageService.getFromLocalStorage('sessionToken') || ''
    return this.getBearerToken(token)
  }

  set sessionToken(token: string) {
    AuthStorageService.saveAuthToStorages('sessionToken', this.getBearerToken(token))
  }

  // Getter and Setter for refreshToken
  get refreshToken(): string {
    return AuthStorageService.getFromLocalStorage('refreshToken') || ''
  }

  set refreshToken(token: string) {
    AuthStorageService.saveAuthToStorages('refreshToken', token)
  }
}

const tokenService: TokenService = new TokenService()
export default tokenService
