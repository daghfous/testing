import { AxiosError, AxiosResponse } from 'axios'
import { defineStore, type StoreGeneric, storeToRefs } from 'pinia'
import { computed, ref } from 'vue'

import { notificationStore } from '@ateme/cathodic-ui/src/components/notifications/notificationStore'
import { IUser } from '@ateme/login-service/src/interfaces/Interfaces'
import tokenService from '@ateme/login-service/src/services/TokenService'
import { usersClient } from '@ateme/login-service/src/config/api'

import { loginServiceStore } from '@store/loginServiceStore'

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
export const usersStore = defineStore('users', () => {
  const storeLoginServiceUsers = loginServiceStore()
  const { getCurrentUser, getIsAdmin } = storeToRefs(storeLoginServiceUsers as StoreGeneric)
  const { fillCurrentUserInfo, updateDetails, updateOwnProfile } = storeLoginServiceUsers
  const { notifySuccess, notifyError } = notificationStore()

  // #####################################
  // STATE
  // #####################################
  const admin = ref<IUser | undefined>(undefined)
  const isLdapUser = ref<boolean>(false)
  const getUsers = computed((): IUser[] => users.value)
  const access = ref<boolean>(false)
  const users = ref<IUser[]>([])

  // #####################################
  // GETTERS
  // #####################################
  const getAdmin = computed((): IUser | undefined => admin.value)
  const getIsLdapUser = computed((): boolean => isLdapUser.value)
  const getAccess = computed((): boolean => access.value)

  // #####################################
  // ACTIONS
  // #####################################
  const setAdmin = (newAdmin: IUser) => (admin.value = newAdmin)
  const setIsLdapUser = (newIsLdapUser: boolean) => (isLdapUser.value = newIsLdapUser)
  const setAccess = (newAccess: boolean) => (access.value = newAccess)
  const setUsers = (newUsers: IUser[]) => (users.value = newUsers)

  /**
   * This method allow to fill all known admin on user store.
   */
  const fillAdmin = async () => {
    try {
      const resp = await usersClient.get('admin', {
        headers: {
          'Content-Type': 'application/json',
          Authorization: tokenService.sessionToken
        }
      })
      if (resp?.status === 200) setAdmin(resp.data)
    } catch (err) {
      await unauthorizedProcess(err as AxiosError)
    }
  }
  const isThisUserTheFirstAdmin = async (username: string): Promise<boolean> => {
    let firstAdminUserName: string = ''
    await usersClient.get('admin').then((resp: AxiosResponse) => {
      return (firstAdminUserName = resp.data.username)
    })
    return username === firstAdminUserName
  }
  /**
   * This method allow to create a user.
   * @param {object} user - user object.
   */
  const create = async (user: Partial<IUser>) => {
    const userData: Partial<IUser> = {
      username: user.username,
      password: user.password,
      scopes: user.roles,
      idp_name: user.idp_name,
      session_timeout_disabled: user.session_timeout_disabled,
      password_expiration_disabled: user.password_expiration_disabled
    }
    if (user.roles) {
      userData.scopes = user.roles
    }
    if (user.level && !user.roles) {
      userData.level = user.level
    }
    try {
      const resp = await usersClient.post('v2/users', userData, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: tokenService.sessionToken
        }
      })
      if (resp?.status === 201) {
        await fillUsers()
        notifySuccess(`User ${user.username} created`)
      }
    } catch (err) {
      await unauthorizedProcess(err as AxiosError)
      notifyError('User creation failed')
    }
  }

  /**
   * This method allow to delete users by id.
   * @param {Array} users - dispatch function.
   */
  const deleteUsers = async (users: Partial<IUser>[]) => {
    const promises: Promise<void>[] = []
    const successDeletedUsers: string[] = []
    users.forEach(user => {
      promises.push(
        usersClient
          .delete(`users/${user.idp_name}/${user.username}`, {
            headers: {
              'Content-Type': 'application/json',
              Authorization: tokenService.sessionToken
            }
          })
          .then((resp: AxiosResponse) => {
            if (resp?.status === 200) {
              if (user.username) successDeletedUsers.push(user.username)
            }
          })
          .catch((err: AxiosError) => {
            notifyError(`User remove failed: ${err?.response?.data ?? err?.message}`, user.username || '')
          })
      )
    })
    // When all promises are done, refresh Users
    await Promise.allSettled(promises)
    await fillUsers()
    notifySuccess('Users deleted', successDeletedUsers.join(', '), false)
  }
  /**
   * This method allow to fill all known user on user store.
   */
  const fillUsers = async () => {
    try {
      const resp = await usersClient.get('users', {
        headers: {
          'Content-Type': 'application/json',
          Authorization: tokenService.sessionToken
        }
      })
      if (resp?.status === 200 && resp?.data?.length > 0) {
        const updatedUsers = resp.data.map((user: IUser) => {
          if (user.scopes) {
            return { ...user, roles: user.scopes }
          }
          return user
        })
        setUsers(updatedUsers)
      }
    } catch (err) {
      await unauthorizedProcess(err as AxiosError)
    }
  }

  /**
   * This method allow to know if current user is an ldap user.
   */
  const fillIsLdapUser = async () => {
    if (!getCurrentUser.value) {
      await fillCurrentUserInfo()
    }
    const newCurrentUser = getCurrentUser.value
    const isLdapUser = !!(newCurrentUser && newCurrentUser?.idp_name && newCurrentUser?.idp_name === 'ldap')

    setIsLdapUser(isLdapUser)
  }
  /**
   * This method allow to update user.
   * @param {IUser} user - The user to edit
   */
  const edit = async (user: Partial<IUser>) => {
    if (getIsAdmin.value) {
      await updateDetails(user)
      await fillUsers()
    }
    if (user?.oldPassword && user?.newPassword) await updateOwnProfile(user)
  }

  /**
   * Backup user configuration.
   * @returns {Promise} - dispatch function.
   */
  const BackupConfiguration = (): Promise<AxiosResponse> => {
    return usersClient.get('fullconfiguration', {
      responseType: 'blob'
    })
  }
  /**
   * Restore user configuration.
   * @param {object} data - the data to restore
   * @returns {Promise<AxiosResponse>} - the response
   */
  const RestoreConfiguration = async (data: object): Promise<AxiosResponse> => {
    return await usersClient.put('fullconfiguration', data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }

  return {
    getAdmin,
    getIsLdapUser,
    getUsers,
    getAccess,
    setAdmin,
    setIsLdapUser,
    setUsers,
    setAccess,
    fillUsers,
    fillAdmin,
    create,
    deleteUsers,
    fillIsLdapUser,
    edit,
    BackupConfiguration,
    RestoreConfiguration,
    isThisUserTheFirstAdmin
  }
})
