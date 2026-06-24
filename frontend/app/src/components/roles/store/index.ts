import { notificationStore } from '@ateme/cathodic-ui/src/components/notifications/notificationStore'
import { AxiosError, AxiosResponse } from 'axios'
import map from 'lodash/map'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useTranslation } from 'i18next-vue'
import { usersClient } from '@ateme/login-service/src/config/api'
import TokenService from '@ateme/login-service/src/services/TokenService'
import { GenericObject } from '@ateme/cathodic-ui/src/interfaces/GenericType'

import { ERoleMode, IBackendPaginatedQuery, IRole, IRoleAction } from '@interfaces/Interfaces'
import { getRangeFromPaginatedQuery } from '@/utils/commonFunctions.ts'
import { IPaginatedQuery } from '@ateme/cathodic-ui/src/interfaces/Table'

const defaultRowPerPage: number = 10
/**
 * User store {roles}.
 * @returns {object} - Roles Store
 */
export const rolesStore = defineStore('roles', () => {
  const { notifySuccess, notifyError } = notificationStore()
  const { t } = useTranslation()

  // -------------------
  // Error handler
  // -------------------
  /**
   * Process error cases of a request.
   * @param {object} resp - Response object.
   */
  const errorInterceptor = async (resp: GenericObject) => {
    const status = resp?.status || resp?.response?.status
    switch (status) {
      case 400:
        notifyError(t('users.errors.badRequest'), resp?.response?.data ?? resp?.message ?? '')
        return
      case 401:
        await TokenService.refreshTokenOrClearStorage()
        return
      case 404:
        notifyError(t('users.errors.notFound'), resp?.response?.data ?? resp?.message ?? '')
        return
      case status >= 500:
        notifyError(`${status} ${t('users.errors.serverError')}`, resp?.response?.data ?? resp?.message ?? '')
        return
    }
  }

  // #####################################
  // STATE
  // #####################################
  const _paginatedRoles = ref<IRole[]>([])
  const _allRoles = ref<IRole[]>([])
  const _actions = ref<IRoleAction[]>([])
  const _isExpertMode = ref<boolean>(false)
  const _numberOfRoles = ref<number>(0)
  const _currentRolesQuery = ref<IPaginatedQuery>({
    rowPerSearch: defaultRowPerPage,
    pageNumber: 1
  })
  const _maxRolesRowPerPage = ref<number | undefined>(undefined)
  // #####################################
  // GETTERS
  // #####################################
  const getPaginatedRoles = computed((): IRole[] => _paginatedRoles.value)
  const getAllRoles = computed((): IRole[] => _allRoles.value)
  const getActions = computed((): IRoleAction[] => _actions.value)
  const getIsExpertMode = computed((): boolean => _isExpertMode.value)
  const getNumberOfRoles = computed((): number => _numberOfRoles.value)
  const getCurrentRolesQuery = computed((): IPaginatedQuery => _currentRolesQuery.value)
  const getMaxRolesRowPerPage = computed((): number | undefined => _maxRolesRowPerPage.value)
  // #####################################
  // ACTIONS
  // #####################################
  const setIsExpertMode = (mode: boolean) => {
    _isExpertMode.value = mode
  }
  const setPaginatedRoles = (roles: IRole[]) => {
    _paginatedRoles.value = roles
  }
  const setAllRoles = (roles: IRole[]) => {
    _allRoles.value = roles
  }
  const setNumberOfRoles = (resp: AxiosResponse) => {
    _numberOfRoles.value = Number(resp.headers['content-range'].split('/')[1])
  }
  const setCurrentRolesQuery = (query: IPaginatedQuery) => {
    _currentRolesQuery.value = query
  }
  const setRolesMaxRowPerPage = (resp: AxiosResponse) => {
    _maxRolesRowPerPage.value = Number(resp.headers['accept-ranges'].split(' ')[1])
  }
  /**
   * @param {Array} actions - the actions array.
   */
  const setActions = (actions: IRoleAction[]) => {
    _actions.value = map(actions, action => {
      return {
        ...action,
        action: `${action.prefix}:${action.name}`,
        policy: 'allow',
        resource: {},
        description: action.description
      }
    })
  }
  /**
   * This method allow to view list of roles.
   * @param {IBackendPaginatedQuery | null} options - The pagination options or none.
   */
  const fillRoles = async (options: IBackendPaginatedQuery | null = null) => {
    await usersClient
      .get('v2/scopes', {
        params: {
          ...options,
          mode: _isExpertMode.value ? ERoleMode.expert : ERoleMode.basic
        },
        headers: {
          'Content-Type': 'application/json',
          Authorization: TokenService.sessionToken
        }
      })
      .then((resp: AxiosResponse) => {
        if (resp.status >= 200 && resp.status < 300) {
          if (options) {
            setPaginatedRoles(resp.data as IRole[])
          } else {
            setAllRoles(resp.data as IRole[])
          }
          setNumberOfRoles(resp)
          setRolesMaxRowPerPage(resp)
        }
      })
      .catch((err: AxiosError) => {
        // Set correct range in case of out of range and refetch
        if (err?.status === 416) {
          setNumberOfRoles(err?.response as AxiosResponse)
          setRolesMaxRowPerPage(err?.response as AxiosResponse)
          fillRoles({ range: getRangeFromPaginatedQuery(getCurrentRolesQuery.value, getNumberOfRoles.value) })
        }
        errorInterceptor(err)
      })
  }
  /**
   * This method allow to view list of actions.
   */
  const fillActions = async () => {
    await usersClient
      .get('actions', {
        headers: {
          'Content-Type': 'application/json',
          Authorization: TokenService.sessionToken
        }
      })
      .then((resp: AxiosResponse) => {
        if (resp.status === 200) {
          setActions(resp.data)
        }
      })
      .catch((err: AxiosError) => {
        errorInterceptor(err)
      })
  }
  /**
   * This method allow to create a new role.
   * @param {object} role - role object.
   */
  const createRole = async (role: IRole) => {
    await usersClient
      .post('v2/scopes', role, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: TokenService.sessionToken
        }
      })
      .then((resp: AxiosResponse) => {
        if (resp.status === 201) {
          notifySuccess('Role created')
        }
      })
      .catch((err: AxiosError) => {
        notifyError("Can't create role")
        errorInterceptor(err)
      })
  }
  /**
   * This method allow to edit a role.
   * @param {object} role - role object.
   */
  const edit = async (role: IRole) => {
    await usersClient
      .patch(`scopes/${role.id}`, role, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: TokenService.sessionToken
        }
      })
      .then(async (resp: AxiosResponse) => {
        if (resp.status === 200) {
          notifySuccess('Role updated')
          await fillRoles()
        }
      })
      .catch((err: AxiosError) => {
        notifyError("Can't update role")
        errorInterceptor(err)
      })
  }
  /**
   * This method allow to delete a list of roles.
   * @param {Array} roles - Array of roles.
   */
  const deleteRoles = async (roles: string[]) => {
    const promises: Promise<unknown>[] = []
    roles.forEach(role => {
      promises.push(
        usersClient
          .delete(`scopes/${role}`, {
            headers: {
              'Content-Type': 'application/json',
              Authorization: TokenService.sessionToken
            }
          })
          .then(() => {
            notifySuccess('Role(s) deleted')
            fillRoles({ range: getRangeFromPaginatedQuery(getCurrentRolesQuery.value, getNumberOfRoles.value) })
          })
          .catch((err: AxiosError) => {
            errorInterceptor(err)
            notifyError("Can't delete role(s)")
          })
      )
    })
    // When all promises are done, refresh Roles
    await Promise.allSettled(promises)
  }

  return {
    getAllRoles,
    getCurrentRolesQuery,
    getPaginatedRoles,
    getActions,
    getIsExpertMode,
    getNumberOfRoles,
    getMaxRolesRowPerPage,
    setCurrentRolesQuery,
    setIsExpertMode,
    fillRoles,
    fillActions,
    createRole,
    edit,
    deleteRoles
  }
})
