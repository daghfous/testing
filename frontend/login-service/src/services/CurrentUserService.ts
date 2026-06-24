import { AxiosError, AxiosResponse } from 'axios'
import AuthStorageService from './AuthStorageService'
import { IRoleAction, IUser } from '../interfaces/Interfaces'
import { usersClient } from '../config/api'
import tokenService from '../services/TokenService'

class CurrentUserService {
  private static actions: IRoleAction[] = []

  /**
   * @static
   * @description Set user data
   * @param {IUser} user - user data
   */
  static setUser(user: IUser) {
    AuthStorageService.addToLocalStorage('currentUserName', user?.username as string)
    AuthStorageService.addToLocalStorage('currentUserIdpName', user?.idp_name as string)
    AuthStorageService.addToLocalStorage('currentUserId', user?.user_id as string)
    AuthStorageService.addToLocalStorage('isTokenActive', 'true')
    AuthStorageService.addToLocalStorage('firstLogin', user.first_login ? user.first_login.toString() : 'false')
    AuthStorageService.addToLocalStorage('passwordExpired', user?.password_expired as string)
    AuthStorageService.addToLocalStorage('preferences', JSON.stringify(user?.preferences))
    AuthStorageService.addToLocalStorage(
      'isAdmin',
      (user?.scopes as string[])?.includes('all:administrator') as unknown as string
    )
    window.dispatchEvent(new CustomEvent('user-management:user-updated', { bubbles: true, detail: { user } }))
  }
  /**
   * Process in case of unauthorized request.
   * @param {AxiosResponse | AxiosError} resp - Response object.
   */
  static async unauthorizedProcess(resp: AxiosResponse | AxiosError) {
    const status = (resp as AxiosResponse)?.status || (resp as AxiosError)?.response?.status
    if (status === 401) {
      await tokenService.refreshTokenOrClearStorage()
    }
  }
  /*
   * This method allow to set user's list of actions.
   */
  static setCurrentUserActions(actions: IRoleAction[]) {
    this.actions = actions
  }

  static getCurrentUserActions() {
    return this.actions
  }
  /*
   * This method allow to view user's list of actions.
   */
  static async fillUserActions() {
    try {
      const resp = await usersClient.get('user/me/actions', {
        headers: { Authorization: tokenService.sessionToken }
      })
      if (resp?.status === 200) {
        this.setCurrentUserActions(resp.data)
      }
    } catch (err) {
      await this.unauthorizedProcess(err as AxiosError)
    }
  }
  /**
   * @static
   * @description Get current user id
   * @returns {string} user id
   */
  static getUserId() {
    return AuthStorageService.getFromLocalStorage('currentUserId')
  }

  /**
   * @static
   * @description Get current user username
   * @returns {string} user username
   */
  static getUsername() {
    return AuthStorageService.getFromLocalStorage('currentUserName')
  }
  /**
   * @static
   * @description Get current user idp_name
   * @returns {string} user idp_name
   */
  static getUserIdpName() {
    return AuthStorageService.getFromLocalStorage('currentUserIdpName')
  }

  /**
   * @static
   * @description Ttest if user is trying to log in for 1st time
   * @returns {boolean} User first login state
   */
  static isFirstLogin() {
    return AuthStorageService.getFromLocalStorage('firstLogin') === 'true'
  }
  /**
   * @static
   * @description Get password Expired state
   * @returns {boolean} user password Expired state
   */
  static isPasswordExpired() {
    return AuthStorageService.getFromLocalStorage('passwordExpired') === 'true'
  }
  /**
   * @static
   * @description Get first login state
   * @returns {boolean} user first login state
   */
  static getFirstLogin() {
    return AuthStorageService.getFromLocalStorage('firstLogin')
  }
  /**
   * @static
   * @description Get is admin
   * @returns {boolean} is user an admin
   */
  static getIsAdmin() {
    return AuthStorageService.getFromLocalStorage('isAdmin')
  }
}
export default CurrentUserService
