import { ADD, API, EDIT, REMOVE, RIGHTS } from '@ateme/login-service/src/services/abilities/constants/common'
export const IDP: string = 'idp'
export const IDP_RIGHTS: string = `${IDP}.${RIGHTS}`
export const IDP_ADD: string = `${IDP}.${ADD}`
export const IDP_REMOVE: string = `${IDP}.${REMOVE}`
export const IDP_EDIT: string = `${IDP}.${EDIT}`
export const GET_IDP_CONFIG_BY_DOMAIN: string = `${IDP}.${API}.GET_IDP_CONFIG_BY_DOMAIN`
export const VALIDATE_IDP: string = `${IDP}.${API}.VALIDATE_IDP`
export default {
  IDP,
  IDP_RIGHTS,
  IDP_ADD,
  IDP_REMOVE,
  IDP_EDIT,

  GET_IDP_CONFIG_BY_DOMAIN,
  VALIDATE_IDP
}
