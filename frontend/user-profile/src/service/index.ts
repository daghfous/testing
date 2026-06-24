import { defineCustomElement } from 'vue'
import ApiClientService from '@ateme/cathodic-ui/src/services/ApiClientService'
import Logger from '@ateme/cathodic-ui/src/services/Logger'
import UserProfile from '@ateme/cathodic-ui/src/components/layouts/topMenu/TopMenuUser.vue'
import { i18n, keyEnUs } from '@ateme/cathodic-ui/src/services/I18nNext'
import TokenService from '@ateme/login-service/src/services/TokenService'
import ActivityService from '@ateme/login-service/src/services/ActivityService'
import CurrentUserService from '@ateme/login-service/src/services/CurrentUserService'
import AuthService from '@ateme/login-service/src/auth/auth'
import { getEnv } from '@ateme/cathodic-ui/src/utils/EnvUtils'
import langMessagesNext from '../lang/index'
import { IUserProfileElement } from '../interfaces/userProfile'
import {
  waitForElement
} from './utils'
/**
 * Service responsible for:
 * - Interacting with the Top Menu API
 * - Managing caching of menu data
 * - Rendering the menu UI component
 * - Handling user-specific menu filtering (based on permissions)
 */
export class UserProfileService {
  private client: ApiClientService
  private refreshIntervalId?: number
  private readonly INACTIVE_USER_TIME_THRESHOLD = -1 // infinite timeout
  private baseUrl = getEnv('BASE_URL')?.replace(/\/+$/, '')

  constructor() {
    // Initialize the API client
    this.client = ApiClientService.getInstance()

    // Register global token retrieval function
    this.client.registerGlobalFunction(
      (config: RequestInit) => config,
      (response: Response) => Promise.resolve(response),
      () => TokenService.sessionToken,
      (response: Response) => Promise.resolve(response.ok)
    )

    // Register API client for user service
    this.client.registerApiClient('userClient', {
      baseUrl: getEnv('USER_MANAGEMENT_URL'),
      responseInterceptor: TokenService.handleResponseInterceptor
    })
  }

  /**
   * Fetch current user profile from the backend.
   * @throws {Error} If the request fails
   * @returns {Promise<void>} - The current user.
   */
  private async getCurrentUser() {
    try {
      const response = await this.client.apiFetch('userClient', 'user/me', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      })
      return response.json()
    } catch (error) {
      Logger.debug('user-profile service/index.ts > getCurrentUser', `Cannot fetch current user: ${error}`)
      throw new Error('Cannot get user info')
    }
  }

  /**
   * Set up the ActivityService to log out the user after a period of inactivity.
   * @param {object} info - Information object
   * @param {boolean} info.timeoutDisabled - Flag indicating if timeout is disabled
   * @returns {Promise<boolean>} - Returns false if timeout is disabled, otherwise sets up the inactivity tracking
   */
  private async setActivityServiceTimeout(info: { timeoutDisabled: boolean }): Promise<boolean> {
    Logger.debug(
      'user-profile service/index.ts > setActivityServiceTimeout',
      `timeoutDisabled is ${String(info.timeoutDisabled)}`
    )
    if (info.timeoutDisabled) {
      Logger.debug('user-profile service/index.ts > setActivityServiceTimeout', 'Session timeout tracking disabled')
      return false
    }
    const inactiveUserAction = () => {
      AuthService.logout(getEnv('BASE_URL')?.replace(/^\/+/, ''))
    }
    let inactivityTimeout = this.INACTIVE_USER_TIME_THRESHOLD
    try {
      const response = await this.client.apiFetch('userClient', 'public/configuration', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      })
      const data = await response.json()
      if (response.status === 200 && data?.logout_timeout > -1) {
        inactivityTimeout = data.logout_timeout * 1000
        Logger.debug(
          'user-profile service/index.ts > setActivityServiceTimeout',
          `Configured inactivity timeout is ${inactivityTimeout}ms`
        )
      }
    } catch (e) {
      Logger.debug('user-profile service/index.ts > setActivityServiceTimeout', `Configuration fetch failed: ${e}`)
      throw new Error(`Cannot get configuration info: ${e}`)
    }
    if (inactivityTimeout > -1) {
      Logger.debug('user-profile service/index.ts > setActivityServiceTimeout', 'Starting ActivityService tracking')
      ActivityService.trackUserActions({
        inactivityTimeout,
        inactiveUserAction
      })
    } else {
      Logger.debug(
        'user-profile service/index.ts > setActivityServiceTimeout',
        'No inactivity timeout configured, tracking not started'
      )
    }
    return true
  }
  /**
   * Update the top menu component with new sections and system name from localStorage.
   * @param {IUserProfileElement} userProfileElement - The top menu element to update
   */
  private initUserProfile(userProfileElement: IUserProfileElement) {
    Logger.debug('user-profile service/index.ts > initUserProfile', 'Initializing user profile element config')
    // User profile config
    const url = window.location.href
    const userProfileUrl =
      `${this.baseUrl}#/users/edit/${CurrentUserService.getUserIdpName()}:${CurrentUserService.getUsername()}`
    userProfileElement.userConfig = {
      userName: CurrentUserService.getUsername() || '',
      onEditProfile: () => location.assign(userProfileUrl),
      onLogout: () => AuthService.logout(getEnv('BASE_URL')?.replace(/^\/+/, ''))
    }
    userProfileElement.appendTo = userProfileElement?.shadowRoot as Element
    if (url.includes(userProfileUrl)) {
      userProfileElement.activeSection = 'editProfile'
      Logger.debug('user-profile service/index.ts > initUserProfile', 'Active section set to editProfile')
    }
  }

  /**
   * Renders the top menu in the DOM.
   * Fetches menu data, sets up event listeners, and handles user interactions.
   * @throws {Error} If the <app-switcher> element is not found or if rendering fails
   */
  async renderUserProfile() {
    Logger.debug('user-profile service/index.ts > renderUserProfile', 'Waiting for user-profile element')
    const userProfileElement = await waitForElement('user-profile', 5000)
    Logger.debug('user-profile service/index.ts > renderUserProfile', 'user-profile element found')
    this.initUserProfile(userProfileElement)
    // Prevent multiple intervals & Refresh menu every 10s
    if (!this.refreshIntervalId) {
      Logger.debug('user-profile service/index.ts > renderUserProfile', 'Starting user refresh interval')
      this.refreshIntervalId = window.setInterval(async () => {
        try {
          await this.getCurrentUser()
        } catch { /* empty */ }
      }, 10000)
    }
    const { session_timeout_disabled } = await this.getCurrentUser()
    Logger.debug(
      'user-profile service/index.ts > renderUserProfile',
      `session_timeout_disabled is ${String(session_timeout_disabled)}`
    )
    await this.setActivityServiceTimeout({
      timeoutDisabled: session_timeout_disabled
    })
  }

  /**
   * Initialize the TopMenuService.
   * Registers the custom element and renders the menu.
   */
  async init() {
    Logger.debug('user-profile service/index.ts > init', 'Registering user-profile custom element')
    const userProfile = defineCustomElement(UserProfile, {
      configureApp(app) {
        i18n(app, { langMessages: langMessagesNext, langLocale: keyEnUs })
      }
    })

    if (!customElements.get('user-profile')) {
      customElements.define('user-profile', userProfile)
      await customElements.whenDefined('user-profile')
      Logger.debug('user-profile service/index.ts > init', 'user-profile custom element registered')
    }

    Logger.debug('user-profile service/index.ts > init', 'Rendering user profile')
    await this.renderUserProfile()
  }
}
