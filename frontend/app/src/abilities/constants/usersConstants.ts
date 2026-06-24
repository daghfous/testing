import { ADD, API, EDIT, REMOVE, RIGHTS } from '@ateme/login-service/src/services/abilities/constants/common'
export const USERS: string = 'users'
export const USERS_RIGHTS: string = `${USERS}.${RIGHTS}`
export const USERS_ADD: string = `${USERS}.${ADD}`
export const USERS_REMOVE: string = `${USERS}.${REMOVE}`
export const USERS_EDIT: string = `${USERS}.${EDIT}`
export const LOGIN: string = `${USERS}.${API}.LOGIN`
export const ADMIN_GET: string = `${USERS}.${API}.GET_ADMIN`
export const CREATE_ADMIN_USER: string = `${USERS}.${API}.CREATE_ADMIN`
export const REMOVE_USER_BY_NAME: string = `${USERS}.${API}.REMOVE_BY_NAME`
export const GET_USER_BY_NAME: string = `${USERS}.${API}.GET_BY_NAME`
export const UPDATE_USER_BY_NAME: string = `${USERS}.${API}.UPDATE_BY_NAME`
export const FORCE_USER_DISCONNECTION: string = `${USERS}.${API}.FORCE_DISCONNECTION`
export const GET_CURRENT_USER: string = `${USERS}.${API}.GET`
export const GET_CURRENT_USER_ACTIONS: string = `${USERS}.${API}.GET_ACTIONS`
export const REACTIVATE_USER_BY_NAME: string = `${USERS}.${API}.REACTIVATE_BY_NAME`
export default {
  USERS,
  USERS_RIGHTS,
  USERS_ADD,
  USERS_REMOVE,
  USERS_EDIT,

  LOGIN,
  ADMIN_GET,
  CREATE_ADMIN_USER,
  REMOVE_USER_BY_NAME,
  GET_USER_BY_NAME,
  UPDATE_USER_BY_NAME,
  FORCE_USER_DISCONNECTION,
  GET_CURRENT_USER,
  GET_CURRENT_USER_ACTIONS,
  REACTIVATE_USER_BY_NAME
}
