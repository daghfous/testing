import { UserRightEnum } from '@ateme/login-service/src/services/abilities/constants/common'
import { setAbilities } from '@ateme/login-service/src/services/abilities/utils'
import idpConstants from '../constants/idpConstants'
import rolesConstants from '../constants/rolesConstants'
import usersConstants from '../constants/usersConstants'
const { EDIT, VIEW } = UserRightEnum
export type UserRightType = (typeof UserRightEnum)[keyof typeof UserRightEnum]

type UserRights = Record<string, UserRightType>

type AbilityFunction = (userRights: UserRights) => void

const abilities: Record<string, AbilityFunction> = {
  // idp
  'usr:validate_idp': userRights => setAbilities(userRights, idpConstants.VALIDATE_IDP, VIEW),
  'usr:get_idp_config_by_domain': userRights => setAbilities(userRights, idpConstants.GET_IDP_CONFIG_BY_DOMAIN, VIEW),
  'usr:get_idp_configs': userRights => setAbilities(userRights, idpConstants.IDP_RIGHTS, VIEW),
  'usr:store_idp_config': userRights => setAbilities(userRights, idpConstants.IDP_ADD, EDIT),
  'usr:remove_idp_config': userRights => setAbilities(userRights, idpConstants.IDP_REMOVE, EDIT),
  'usr:update_idp_config': userRights => setAbilities(userRights, idpConstants.IDP_EDIT, EDIT),

  // roles
  'usr:get_scopes': userRights => setAbilities(userRights, rolesConstants.ROLES_RIGHTS, VIEW),
  'usr:store_scopes': userRights => setAbilities(userRights, rolesConstants.ROLES_ADD, EDIT),
  'usr:remove_scopes': userRights => setAbilities(userRights, rolesConstants.ROLES_REMOVE, EDIT),
  'usr:remove_scope_by_id': userRights => setAbilities(userRights, rolesConstants.REMOVE_ROLE_BY_ID, EDIT),
  'usr:update_scope_by_id': userRights => setAbilities(userRights, rolesConstants.ROLES_EDIT, EDIT),
  'usr:get_scope_by_id': userRights => setAbilities(userRights, rolesConstants.GET_ROLE_BY_ID, VIEW),

  // users
  'usr:get_users': userRights => setAbilities(userRights, usersConstants.USERS_RIGHTS, VIEW),
  'usr:add_users': userRights => setAbilities(userRights, usersConstants.USERS_ADD, EDIT),
  'usr:delete_users': userRights => setAbilities(userRights, usersConstants.USERS_REMOVE, EDIT),
  'usr:remove_user_by_name': userRights => setAbilities(userRights, usersConstants.REMOVE_USER_BY_NAME, EDIT),
  'usr:get_user_by_name': userRights => setAbilities(userRights, usersConstants.GET_USER_BY_NAME, VIEW),
  'usr:update_user_by_name': userRights => setAbilities(userRights, usersConstants.UPDATE_USER_BY_NAME, EDIT),
  'usr:force_user_disconnection': userRights => setAbilities(userRights, usersConstants.FORCE_USER_DISCONNECTION, EDIT),
  'usr:get_current_user': userRights => setAbilities(userRights, usersConstants.GET_CURRENT_USER, VIEW),
  'usr:get_current_user_actions': userRights => setAbilities(userRights, usersConstants.GET_CURRENT_USER_ACTIONS, VIEW),
  'usr:login': userRights => setAbilities(userRights, usersConstants.LOGIN, VIEW),
  'usr:reactivate_user_by_name': userRights => setAbilities(userRights, usersConstants.REACTIVATE_USER_BY_NAME, EDIT),

  // admin
  'usr:get_admin': userRights => setAbilities(userRights, usersConstants.ADMIN_GET, VIEW),
  'usr:create_admin_user': userRights => setAbilities(userRights, usersConstants.CREATE_ADMIN_USER, EDIT)
}

export default abilities
