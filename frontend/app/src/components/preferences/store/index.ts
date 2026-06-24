import { notificationStore } from '@ateme/cathodic-ui/src/components/notifications/notificationStore'

import { AxiosResponse } from 'axios'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { usersClient } from '@ateme/login-service/src/config/api'
import configurationConstants from '../constants'
import { IUnknownObjectKeys } from '@interfaces/Interfaces'
import { ITimeoutConfiguration } from '@ateme/login-service/src/interfaces/Interfaces'

/**
 * Common configuration store.
 */
export const configurationsStore = defineStore('configurations', () => {
  const { notifySuccess, notifyError } = notificationStore()

  // #####################################
  // STATE
  // #####################################
  const _data = ref<ITimeoutConfiguration>({} as ITimeoutConfiguration)
  const _logoutTimeoutInfiniteOptionEnabled = ref<boolean>(false)
  const _logoutTimeout = ref<number>(0)
  const _refreshTokenExpiration = ref<number>(0)
  const _userDeactivationPeriod = ref<number>(0)
  const _maxSuccessiveFailedLogin = ref<number>(0)
  const _enableUserDeactivation = ref<boolean>(false)
  const _passwordExpiration = ref<number>(0)
  const _passwordMinLength = ref<number>(10)
  // #####################################
  // GETTERS
  // #####################################
  const getData = computed((): ITimeoutConfiguration => _data.value)
  const getLogoutTimeoutInfiniteOptionEnabled = computed((): boolean => _logoutTimeoutInfiniteOptionEnabled.value)
  const getRefreshTokenExpiration = computed((): number => _refreshTokenExpiration.value)
  const getLogoutTimeout = computed((): number => _logoutTimeout.value)
  const getUserDeactivationPeriod = computed((): number => _userDeactivationPeriod.value)
  const getMaxSuccessiveFailedLogin = computed((): number => _maxSuccessiveFailedLogin.value)
  const getEnableUserDeactivation = computed((): boolean => _enableUserDeactivation.value)
  const getPasswordExpiration = computed((): number => _passwordExpiration.value)
  const getPasswordMinLength = computed((): number => _passwordMinLength.value)

  // #####################################
  // ACTIONS
  // #####################################
  const updateLogoutTimeout = (newLogoutTimeout: number) => {
    _logoutTimeout.value = newLogoutTimeout
  }
  /**
   * @description Update "logoutTimeout" key
   * @param {number} newRefreshTokenExpiration - new value for "refreshTokenExpiration" key
   */
  const updateRefreshTokenExpiration = (newRefreshTokenExpiration: number) => {
    _refreshTokenExpiration.value = newRefreshTokenExpiration
  }
  /**
   * @description Update "userDeactivationPeriod" key
   * @param {number} newUserDeactivationPeriod - new value for "userDeactivationPeriod" key
   */
  const updateUserDeactivationPeriod = (newUserDeactivationPeriod: number) => {
    _userDeactivationPeriod.value = newUserDeactivationPeriod
    _enableUserDeactivation.value = _userDeactivationPeriod.value >= 0
  }
  /**
   * @description Update "maxSuccessiveFailedLogin" key
   * @param {number} newMaxSuccessiveFailedLogin - new value for "maxSuccessiveFailedLogin" key
   */
  const updateMaxSuccessiveFailedLogin = (newMaxSuccessiveFailedLogin: number) => {
    _maxSuccessiveFailedLogin.value = newMaxSuccessiveFailedLogin
  }
  /**
   * Updates the timeout configuration.
   * @param {number} newTimeoutConfiguration - The new number
   */
  const updateTimeoutConfiguration = async (newTimeoutConfiguration: ITimeoutConfiguration) => {
    if (
      (newTimeoutConfiguration.refresh_token_expiration as number) <=
      Number(configurationConstants.values.logoutTimeoutOptions.oneHour.value)
    ) {
      newTimeoutConfiguration.token_expiration = (newTimeoutConfiguration.refresh_token_expiration as number) / 2
    } else {
      newTimeoutConfiguration.token_expiration = 3600
    }
    await usersClient
      .put('configuration', newTimeoutConfiguration)
      .then(() => {
        updateLogoutTimeout(newTimeoutConfiguration.logout_timeout as number)
        updateRefreshTokenExpiration(newTimeoutConfiguration.refresh_token_expiration as number)
        updateUserDeactivationPeriod(newTimeoutConfiguration.user_deactivation_period)
        updateMaxSuccessiveFailedLogin(newTimeoutConfiguration.max_successive_failed_login)
        updatePwdPolicy(newTimeoutConfiguration)
        notifySuccess('Configuration saved')
      })
      .catch(() => notifyError("Can't save configuration"))
  }
  /**
   * fill timeout configuration.
   * @param {boolean} [isPublic] - Is the configuration public
   */
  const fillTimeoutConfiguration = async (isPublic: boolean = false) => {
    const confPath: string = isPublic ? 'public/configuration' : 'configuration'
    await usersClient.get(confPath).then((res: AxiosResponse) => {
      updateConfiguration(res?.data)
      updateLogoutTimeout(res?.data?.logout_timeout as number)
      updateRefreshTokenExpiration(res?.data?.refresh_token_expiration as number)
      updateUserDeactivationPeriod(res?.data?.user_deactivation_period)
      updateMaxSuccessiveFailedLogin(res?.data?.max_successive_failed_login)
      updatePasswordExpiration(res?.data?.password_policy.expiration_delay_in_days)
      updatePasswordMinLength(res?.data?.password_policy.password_min_length)
    })
  }
  /**
   * @description Update "Password Expiration" key
   * @param {string} data - new value for "Password Expiration" key
   */
  const updatePasswordExpiration = (data: number) => {
    _passwordExpiration.value = data
  }
  /**
   * @description Update "PasswordMinLength" key
   * @param {string} data - new value for "PasswordMinLength" key
   */
  const updatePasswordMinLength = (data: number) => {
    _passwordMinLength.value = data
  }

  const updatePwdPolicy = async (data: IUnknownObjectKeys) => {
    const forceChangePwd = data.force_change_password
    delete data.force_change_password
    return await usersClient
      .put('configuration', data, {
        params: {
          force_change_password: forceChangePwd
        }
      })
      .then(() => {
        updatePasswordExpiration(data?.password_policy?.expiration_delay_in_days)
        updatePasswordMinLength(data?.password_policy?.password_min_length)
      })
  }

  const updateConfiguration = (data: ITimeoutConfiguration) => {
    _data.value = data
  }

  return {
    getLogoutTimeoutInfiniteOptionEnabled,
    getRefreshTokenExpiration,
    getLogoutTimeout,
    getUserDeactivationPeriod,
    getMaxSuccessiveFailedLogin,
    getEnableUserDeactivation,
    getPasswordExpiration,
    getPasswordMinLength,
    getData,
    updateLogoutTimeout,
    updateRefreshTokenExpiration,
    updateUserDeactivationPeriod,
    updateMaxSuccessiveFailedLogin,
    updateTimeoutConfiguration,
    fillTimeoutConfiguration,
    updatePwdPolicy
  }
})
