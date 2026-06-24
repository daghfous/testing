import { AxiosError, AxiosResponse } from 'axios'
import cloneDeep from 'lodash/cloneDeep'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { notificationStore } from '@ateme/cathodic-ui/src/components/notifications/notificationStore'
import { usersClient } from '@ateme/login-service/src/config/api'
import { IUser } from '@ateme/login-service/src/interfaces/Interfaces'
import TokenService from '@ateme/login-service/src/services/TokenService'
import { IAttributes, IIdp, IIdpMapper } from '@interfaces/Interfaces'
import { compareObjects } from '../../../utils/commonFunctions'

/**
 * Process in case of unauthorized request.
 * @param {object} resp - Response object.
 */
const unauthorizedProcess = (resp: AxiosError | AxiosResponse) => {
  const status = resp?.status // || resp?.response?.status
  if (status === 401) {
    TokenService.refreshTokenOrClearStorage()
  }
}
/**
 * User store {idp}.
 * @returns {object} - idp Store
 */
export const idpStore = defineStore('idp', () => {
  const { notifySuccess, notifyError } = notificationStore()

  const _idps = ref<IIdp[]>([])
  /**
   * @param {object} state - the store.
   * @returns {Array} - idps.
   */
  const getIdPs = computed((): IIdp[] => _idps.value)
  /**
   * Change idp.roles to idp.scopes and format mappers
   * @param {IIdp} idp - the idp.
   * @returns {IIdp} - parsed idp
   */
  const formatIdpForApi = (idp: IIdp): IIdp => {
    const data: IIdp = cloneDeep(idp)
    formatMappersForApi(data)
    data.scopes = data.roles
    delete data.roles
    return data
  }
  /**
   * Change idp.scopes to idp.roles and format mappers
   * @param {IIdp} idp - the idp.
   * @returns {IIdp} - parsed idp
   */
  const formatIdpForFrontend = (idp: IIdp): IIdp => {
    const data = cloneDeep(idp)
    formatMappersForFrontend(data)
    data.roles = data.scopes
    delete data.scopes
    return data
  }
  /**
   * Format mappers of the given IDP in API format.
   * @example
   * formatMappersForApi({
   *   type: 'simple',
   *   attribute_name: 'foo',
   *   attribute_value: 'bar',
   *   roles_to_add: ['admin', 'user']
   * });
   * // returns {
   * //   type: 'simple',
   * //   attributes: [{ name: 'foo', value: 'bar' }],
   * //   scopes_to_add: ['admin', 'user']
   * // }
   * @param {object} idp The IDP to parse
   * @returns {object} The formatted IDP
   */
  const formatMappersForApi = (idp: IIdp): IIdp => {
    ;(idp.mappers ?? []).forEach(mapper => {
      if (mapper.type === 'direct') {
        delete mapper['attribute_value']
        delete mapper['roles_to_add']
      } else {
        if (!mapper.attributes) {
          mapper.attributes = [{ name: mapper.attribute_name, value: mapper.attribute_value }]
        }
        delete mapper['attribute_name']
        delete mapper['attribute_value']
        mapper.scopes_to_add = mapper.roles_to_add
        delete mapper.roles_to_add
      }
    })
    return idp
  }
  /**
   * Format mappers of the given IDP in frontend format
   * @example
   * formatMappersForFrontend({
   *   type: 'simple',
   *   attributes: [{ name: 'foo', value: 'bar' }],
   *   scopes_to_add: ['admin', 'user']
   * });
   * // returns {
   * //   type: 'simple',
   * //   attribute_name: 'foo',
   * //   attribute_value: 'bar',
   * //   roles_to_add: ['admin', 'user']
   * // }
   * @param {object} idp The IDP to parse
   * @returns {object} The formatted IDP
   */
  const formatMappersForFrontend = (idp: IIdp): IIdp => {
    const data: IIdp = idp
    ;(data.mappers ?? []).forEach((mapper: IIdpMapper) => {
      if (mapper.type === 'simple') {
        mapper.attribute_name = (mapper.attributes as IAttributes[])[0].name
        mapper.attribute_value = (mapper.attributes as IAttributes[])[0].value
        delete mapper['attributes']
        mapper.roles_to_add = mapper.scopes_to_add
        delete mapper.scopes_to_add
      }
    })
    return data
  }
  /**
   * Initialize idp.
   * @param {object} data - idp object.
   * @returns {Array} - Lists of updated idps
   */
  const initializeIdP = async (data: IIdp) => {
    const idp = formatIdpForApi(data)
    await usersClient
      .post('idpconfigs', idp, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: TokenService.sessionToken
        }
      })
      .then((response: AxiosResponse) => {
        unauthorizedProcess(response)
        notifySuccess('IdP configuration saved')
        fillIdPs()
      })
      .catch((err: AxiosError) => {
        unauthorizedProcess(err)
        notifyError("Can't create IdP configuration")
        throw new Error(err.message)
      })
  }
  /**
   * Validate idp config.
   * @param {object} data - data object.
   */
  const validateIdP = async (data: Partial<IIdp> & Partial<IUser>) => {
    const idp = formatIdpForApi(data)
    await usersClient
      .post('idpconfigs/validate', idp, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: TokenService.sessionToken
        }
      })
      .then((response: AxiosResponse) => {
        const res = response?.request?.response
        if (response?.status === 200) {
          notifySuccess('IDP config is valid')
        } else if (response?.status !== 200) {
          notifyError(res)
        }
        unauthorizedProcess(response)
      })
      .catch(err => {
        notifyError(err?.response?.data ?? err?.message)
      })
  }
  /**
   * Update idp config.
   * @param {object} model - model object.
   * @returns {Array} list of updated idps
   */
  const updateIdP = async (model: IIdp): Promise<IIdp[] | void> => {
    let modelChanges = {}
    // Get the idp config before the update and compare with the new one to get the only the changes
    const current: IIdp = _idps.value.find(item => item.idp_name === model.idp_name) || {}
    if (current) {
      modelChanges = compareObjects(current, model)
    }
    if (!modelChanges) return
    let idp = formatIdpForApi(modelChanges)
    // Add the idp_type required by the backend
    if (!idp) {
      idp = {}
    }
    idp.idp_type = current.idp_type
    return await usersClient
      .patch(`idpconfigs/${model.idp_name}?update_users_scopes=${!!model.roles_updated}`, idp, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: TokenService.sessionToken
        }
      })
      .then(async (resp: AxiosResponse) => {
        const statusCode = resp?.status //|| resp?.response?.status
        notifySuccess('IdP configuration updated')
        if (statusCode === 200) {
          return await fillIdPs()
        }
        unauthorizedProcess(resp)
      })
      .catch((err: AxiosError) => {
        notifyError("Can't update IdP configuration")
        throw new Error(err?.message)
      })
  }
  /**
   * Get all idps configs.
   */
  const fillIdPs = async () => {
    await usersClient
      .get('idpconfigs', {
        headers: {
          'Content-Type': 'application/json',
          Authorization: TokenService.sessionToken
        }
      })
      .then((resp: AxiosResponse) => {
        if (resp?.status === 200 && resp.data.length > 0) {
          _idps.value = resp.data.map((idp: IIdp) => formatIdpForFrontend(idp))
        }
        unauthorizedProcess(resp)
      })
      .catch((err: AxiosError) => {
        unauthorizedProcess(err)
        throw new Error(err?.message)
      })
  }
  /**
   * Get a idp config by idp_name.
   * @param {string} idp_name - idp object.
   * @returns {object} - the idp
   */
  const getIdpByIdpName = async (idp_name: string): Promise<IIdp> => {
    return (await usersClient
      .get(`idpconfigs/${idp_name}`, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: TokenService.sessionToken
        }
      })
      .then((resp: AxiosResponse) => {
        if (resp?.status === 200) {
          return formatIdpForFrontend(resp.data)
        }
        unauthorizedProcess(resp)
      })
      .catch((err: AxiosError) => {
        unauthorizedProcess(err)
      })) as IIdp
  }
  /**
   * Get SP metadata.
   * @param {string} idp_name - idp object.
   * @returns {string} sp metadata of an idp
   */
  const getSpMetadata = async (idp_name: string): Promise<string> => {
    return await usersClient
      .get(`idp_metadata/${idp_name}`, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: TokenService.sessionToken
        },
        params: {
          relay_state: `${window.location.origin}/${window.location.pathname.split('/')[1]}`
        }
      })
      .then((resp: AxiosResponse) => {
        if (resp?.status === 200 && resp.data.length > 0) {
          return resp.data
        }
        unauthorizedProcess(resp)
      })
      .catch((err: AxiosError) => {
        unauthorizedProcess(err)
      })
  }
  /**
   * Delete a idp config.
   * @param {string} idp_name - idp object.
   */
  const deleteIdP = (idp_name: string) => {
    usersClient
      .delete(`idpconfigs/${idp_name}`, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: TokenService.sessionToken
        }
      })
      .then((resp: AxiosResponse) => {
        if (resp?.status === 200) {
          fillIdPs()
        }
        notifySuccess(`IdP ${idp_name} deleted`)
        unauthorizedProcess(resp)
      })
      .catch((err: AxiosError) => {
        notifyError(`Can't delete IdP ${idp_name}`)
        unauthorizedProcess(err)
      })
  }

  return {
    getIdPs,
    initializeIdP,
    validateIdP,
    updateIdP,
    fillIdPs,
    getIdpByIdpName,
    getSpMetadata,
    deleteIdP
  }
})
