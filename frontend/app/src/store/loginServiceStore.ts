import { notificationStore } from '@ateme/cathodic-ui/src/components/notifications/notificationStore.ts'
import axios, { AxiosError, AxiosResponse } from 'axios'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { usersClient } from '@ateme/login-service/src/config/api'
import { IRoleAction, IUnknownObjectKeys, IUser } from '@ateme/login-service/src/interfaces/Interfaces.ts'
import AuthStorageService from '@ateme/login-service/src/services/AuthStorageService'
import CurrentUserService from '@ateme/login-service/src/services/CurrentUserService'
import tokenService from '@ateme/login-service/src/services/TokenService'

/**
 * Process in case of unauthorized request.
 * @param {object} resp - Response object.
 */
const unauthorizedProcess = async (resp: AxiosResponse | AxiosError) => {
  const status = (resp as AxiosResponse)?.status || (resp as AxiosError)?.response?.status
  if (status === 401) {
    await tokenService.refreshTokenOrClearStorage()
  }
}

/**
 * User store {users}.
 * @returns {object} - User Store
 */
export const loginServiceStore = defineStore('loginServiceStore', () => {
  const { notifySuccess, notifyError } = notificationStore()

  // #####################################
  // STATE
  // #####################################
  const configuration = ref<IUnknownObjectKeys>({})
  const firstUser = ref<boolean>(false)
  const ping = ref<boolean>(false)
  const isAdmin = ref<boolean>(false)
  const currentUser = ref<IUser | undefined>(undefined)
  const currentUserActions = ref<IRoleAction[]>([])

  // #####################################
  // GETTERS
  // #####################################
  const getConfiguration = computed((): IUnknownObjectKeys => configuration.value)
  const getFirstUser = computed((): boolean => firstUser.value)
  const getPing = computed((): boolean => ping.value)
  const getCurrentUser = computed((): IUser | undefined => currentUser.value)
  const getIsAdmin = computed((): boolean => isAdmin.value)
  const getCurrentUserActions = computed((): IRoleAction[] => currentUserActions.value)

  // #####################################
  // ACTIONS
  // #####################################
  const setFirstUser = (newFirstUser: boolean) => (firstUser.value = newFirstUser)
  const setPing = (newPing: boolean) => (ping.value = newPing)
  const setCurrentUser = (newUser: IUser) => (currentUser.value = newUser)
  const setIsAdmin = (newIsAdmin: boolean) => (isAdmin.value = newIsAdmin)
  const setCurrentUserActions = (actions: IRoleAction[]) => (currentUserActions.value = actions)

  /**
   * This method allow to catch if an admin user already exist or not.
   */
  const isAlreadyAnAdmin = async () => {
    await usersClient
      .get('admin')
      .then(resp => {
        if (resp?.status === 200) {
          setFirstUser(false)
        }
      })
      .catch(err => {
        if (err?.response?.status === 404) {
          setFirstUser(true)
        } else {
          setFirstUser(false)
        }
      })
  }
  /**
   * This method allow to view user's list of actions.
   */
  const fillUserActions = async () => {
    try {
      const resp = await usersClient.get('user/me/actions', {
        headers: { Authorization: tokenService.sessionToken }
      })
      if (resp?.status === 200) {
        setCurrentUserActions(resp.data)
      }
    } catch (err) {
      notifyError((err as AxiosError)?.response?.data as string)
      await unauthorizedProcess(err as AxiosError)
    }
  }
  /**
   * This method allow to create an admin user at first connection.
   * @param {Partial<IUser>} user - user object.
   */
  const createAdmin = async (user: Partial<IUser>) => {
    const dataToSend: Partial<IUser> = {
      username: user.username,
      password: user.password,
      level: user.level,
      idp_name: 'local'
    }
    try {
      const resp = await usersClient.post('admin', dataToSend, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: tokenService.sessionToken
        }
      })
      if (resp?.status === 201) {
        await isAlreadyAnAdmin()
        notifySuccess(`Administrator ${user.username} created`)
        location.reload()
      }
    } catch (err) {
      await unauthorizedProcess(err as AxiosError)
      notifyError("Can't create admin")
    }
  }
  /**
   * Launch user ping.
   * @returns {Promise} - dispatch function.
   */
  const userPing = async (): Promise<void> => {
    try {
      await usersClient.get('ping')
      setPing(true)
    } catch {
      setPing(false)
    }
  }
  /**
   * This method allow to update user's data.
   * @param {Partial<IUser>} user - user object.
   */
  const updateDetails = async (user: Partial<IUser>) => {
    const data: Partial<IUser> = {
      scopes: user.roles,
      idp_name: user.idp_name,
      level: user.level,
      password: user.newPassword,
      first_login: user.first_login,
      session_timeout_disabled: user.session_timeout_disabled,
      password_expiration_disabled: user.password_expiration_disabled
    }
    try {
      const resp = await usersClient.patch(`users/${user.idp_name}/${user.username}`, data, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: tokenService.sessionToken
        }
      })
      if (resp?.status === 200) {
        notifySuccess(`User ${user.username} updated`)
      } else {
        notifyError("Can't update user")
      }
    } catch (err) {
      await unauthorizedProcess(err as AxiosError)
      notifyError("Can't update user")
    }
  }
  /**
   * This method allow to update own user's password.
   * @param {Partial<IUser>} user - user to update password.
   * @returns {Promise} - dispatch function.
   */
  const updateOwnProfile = async (user: Partial<IUser>) => {
    const dataToSend = {
      old_password: user.oldPassword,
      new_password: user.password || user.newPassword
    }
    if (dataToSend.new_password && dataToSend.new_password !== dataToSend.old_password) {
      return (
        usersClient
          .patch('user/me/password', dataToSend, {
            headers: {
              'Content-Type': 'application/json',
              Authorization: tokenService.sessionToken
            }
          })
          .then(resp => {
            if (resp?.status === 200) {
              AuthStorageService.clearAuthAndUserDataFromStorages()
              location.reload()
            } else {
              throw new Error('Incorrect login or password')
            }
          })
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          .catch((err: AxiosError<any, any>) => {
            unauthorizedProcess(err)
            throw new Error(err?.response?.data)
          })
      )
    }
  }
  /**
   * This method allow to know if current user is admin.
   */
  const fillIsAdmin = async () => {
    if (!currentUser.value) {
      await fillCurrentUserInfo()
    }
    const isAdmin: boolean = !!(
      currentUser.value?.scopes &&
      (currentUser.value.scopes.includes('all:administrator') || currentUser.value.scopes.includes('usr:administrator'))
    )
    setIsAdmin(isAdmin)
  }
  /**
   * This method allow to fill current user info.
   */
  const fillCurrentUserInfo = async () => {
    try {
      const resp: IUnknownObjectKeys = await usersClient.get('user/me', {
        headers: {
          'Content-Type': 'application/json',
          Authorization: tokenService.sessionToken
        }
      })
      if (resp?.status === 200) {
        setCurrentUser(resp.data)
        CurrentUserService.setUser(resp.data)
        AuthStorageService.writeUserDataInSessionStorage()
        if (CurrentUserService.isFirstLogin() && !location.href.includes('/firstLogin')) {
          location.reload()
        } else if (CurrentUserService.isPasswordExpired() && !location.href.includes('/passwordExpiration')) {
          location.reload()
        }
        await fillIsAdmin()
      }
    } catch (err) {
      await unauthorizedProcess(err as AxiosError)
    }
  }

  /**
   * get authentication configuration.
   */
  const fillConfiguration = async () => {
    await usersClient.get('public/configuration').then((res: AxiosResponse) => {
      updateConfiguration(res?.data)
    })
  }
  const updateConfiguration = (data: IUnknownObjectKeys) => {
    configuration.value = data
  }
  /**
   * This method allow to logout.
   */
  const logout = async () => {
    try {
      const resp: IUnknownObjectKeys = await usersClient.delete('logout', {
        headers: {
          'Content-Type': 'application/json',
          Authorization: tokenService.sessionToken
        },
        params: {
          relay_state: `${window.location.origin}/${window.location.pathname.split('/')[1]}`
        }
      })
      AuthStorageService.clearAuthAndUserDataFromStorages()
      if (resp?.data?.slo_url) {
        window.location.href = resp.data.slo_url
      } else {
        location.reload()
      }
      delete axios.defaults.headers.common['Authorization']
    } catch {
      AuthStorageService.clearAuthAndUserDataFromStorages()
      location.reload()
    }
  }

  return {
    getPing,
    getFirstUser,
    getIsAdmin,
    getCurrentUser,
    getCurrentUserActions,
    getConfiguration,
    setCurrentUserActions,
    fillIsAdmin,
    isAlreadyAnAdmin,
    createAdmin,
    updateDetails,
    updateOwnProfile,
    userPing,
    fillCurrentUserInfo,
    fillUserActions,
    fillConfiguration,
    logout
  }
})
