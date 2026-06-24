import globalConstants from '../constants'
import { UserRightEnum } from '../constants/common'
import { setAbilities, UserRightType } from '../utils'

const { EDIT, VIEW } = UserRightEnum

type UserRights = Record<string, UserRightType>

type AbilityFunction = (userRights: UserRights) => void

const abilities: Record<string, AbilityFunction> = {
  // global
  'usr:get_def': userRights => setAbilities(userRights, globalConstants.GET_DEF, VIEW),
  'usr:get_doc': userRights => setAbilities(userRights, globalConstants.GET_DOC, VIEW),
  'usr:get_ping': userRights => setAbilities(userRights, globalConstants.GET_PING, VIEW),
  'usr:get_actions': userRights => setAbilities(userRights, globalConstants.ACTIONS_GET, VIEW),
  'usr:post_api_definition': userRights => setAbilities(userRights, globalConstants.POST_API_DEFINITION, VIEW),
  'usr:get_configuration': userRights => setAbilities(userRights, globalConstants.GET_CONFIGURATION, VIEW),
  'usr:update_configuration': userRights => setAbilities(userRights, globalConstants.UPDATE_CONFIGURATION, EDIT),

  // profile
  'usr:logout': userRights => setAbilities(userRights, globalConstants.LOGOUT, EDIT),
  'usr:change_password': userRights => setAbilities(userRights, globalConstants.CHANGE_PASSWORD, EDIT),

  // token
  'usr:refresh_token': userRights => setAbilities(userRights, globalConstants.REFRESH_TOKEN, VIEW),
  'usr:token_introspection': userRights => setAbilities(userRights, globalConstants.TOKEN_INTROSPECTION, VIEW),
  'usr:change_token_expiration': userRights => setAbilities(userRights, globalConstants.CHANGE_TOKEN_EXPIRATION, EDIT)
}

export default abilities
