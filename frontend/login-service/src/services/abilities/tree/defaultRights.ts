import { IUnknownObjectKeys } from '../../../interfaces/Interfaces'
import { API, UserRightEnum } from '../constants/common'

const { HIDDEN } = UserRightEnum

const defaultRightsObject: IUnknownObjectKeys = {
  [API]: {
    GET_GLOBAL_DEF: HIDDEN,
    GET_GLOBAL_DOC: HIDDEN,
    GET_GLOBAL_PING: HIDDEN,
    GET_ACTIONS: HIDDEN,
    POST_DEFINITION: HIDDEN,
    GET_CONFIGURATION: HIDDEN,
    UPDATE_CONFIGURATION: HIDDEN,

    REFRESH_TOKEN: HIDDEN,
    TOKEN_INTROSPECTION: HIDDEN,
    CHANGE_TOKEN_EXPIRATION: HIDDEN,

    CHANGE_PASSWORD: HIDDEN,
    LOGOUT: HIDDEN
  }
}
export default defaultRightsObject
