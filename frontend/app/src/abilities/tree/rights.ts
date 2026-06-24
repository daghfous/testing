import {
  ADD,
  API,
  EDIT,
  REMOVE,
  RIGHTS,
  UserRightEnum
} from '@ateme/login-service/src/services/abilities/constants/common'
import idpConstants from '../constants/idpConstants'
import rolesConstants from '../constants/rolesConstants'
import usersConstants from '../constants/usersConstants'
import { IUnknownObjectKeys } from '@interfaces/Interfaces'

const { HIDDEN } = UserRightEnum
const RightsObject: IUnknownObjectKeys = {
  [idpConstants.IDP]: {
    [RIGHTS]: HIDDEN,
    [ADD]: HIDDEN,
    [REMOVE]: HIDDEN,
    [EDIT]: HIDDEN,
    [API]: {
      GET_IDP_CONFIG_BY_DOMAIN: HIDDEN,
      VALIDATE_IDP: HIDDEN
    }
  },
  [rolesConstants.ROLES]: {
    [RIGHTS]: HIDDEN,
    [ADD]: HIDDEN,
    [REMOVE]: HIDDEN,
    [EDIT]: HIDDEN,
    [API]: {
      REMOVE_BY_ID: HIDDEN,
      GET_BY_ID: HIDDEN
    }
  },
  [usersConstants.USERS]: {
    [RIGHTS]: HIDDEN,
    [ADD]: HIDDEN,
    [REMOVE]: HIDDEN,
    [EDIT]: HIDDEN,
    [API]: {
      LOGIN: HIDDEN,
      GET_ADMIN: HIDDEN,
      CREATE_ADMIN: HIDDEN,
      REMOVE_BY_NAME: HIDDEN,
      GET_BY_NAME: HIDDEN,
      UPDATE_BY_NAME: HIDDEN,
      FORCE_DISCONNECTION: HIDDEN,
      GET: HIDDEN,
      GET_ACTIONS: HIDDEN,
      REACTIVATE_BY_NAME: HIDDEN
    }
  }
}
export default RightsObject
