import { API } from './common'
export const GET_DEF: string = `${API}.GET_GLOBAL_DEF`
export const GET_DOC: string = `${API}.GET_GLOBAL_DOC`
export const GET_PING: string = `${API}.GET_GLOBAL_PING`
export const ACTIONS_GET: string = `${API}.GET_ACTIONS`
export const POST_API_DEFINITION: string = `${API}.POST_DEFINITION`
export const GET_CONFIGURATION: string = `${API}.GET_CONFIGURATION`
export const UPDATE_CONFIGURATION: string = `${API}.UPDATE_CONFIGURATION`

export const REFRESH_TOKEN: string = `${API}.REFRESH_TOKEN`
export const TOKEN_INTROSPECTION: string = `${API}.TOKEN_INTROSPECTION`
export const CHANGE_TOKEN_EXPIRATION: string = `${API}.CHANGE_TOKEN_EXPIRATION`

export const CHANGE_PASSWORD: string = 'changePassword'
export const LOGOUT: string = 'logout'

export default {
  GET_DEF,
  GET_DOC,
  GET_PING,
  ACTIONS_GET,
  POST_API_DEFINITION,
  GET_CONFIGURATION,
  UPDATE_CONFIGURATION,

  REFRESH_TOKEN,
  TOKEN_INTROSPECTION,
  CHANGE_TOKEN_EXPIRATION,

  CHANGE_PASSWORD,
  LOGOUT
}
