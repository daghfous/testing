import { ADD, API, EDIT, REMOVE, RIGHTS } from '@ateme/login-service/src/services/abilities/constants/common'
export const ROLES: string = 'scopes'
export const ROLES_RIGHTS: string = `${ROLES}.${RIGHTS}`
export const ROLES_ADD: string = `${ROLES}.${ADD}`
export const ROLES_REMOVE: string = `${ROLES}.${REMOVE}`
export const ROLES_EDIT: string = `${ROLES}.${EDIT}`
export const ALL_KEY: string = 'all:'
export const ALL_ADMIN_KEY: string = 'all:administrator'
export const REMOVE_ROLE_BY_ID: string = `${ROLES}.${API}.REMOVE_BY_ID`
export const GET_ROLE_BY_ID: string = `${ROLES}.${API}.GET_BY_ID`
export default {
  ROLES,
  ROLES_RIGHTS,
  ROLES_ADD,
  ROLES_REMOVE,
  ROLES_EDIT,

  ALL_KEY,
  ALL_ADMIN_KEY,
  REMOVE_ROLE_BY_ID,
  GET_ROLE_BY_ID
}
