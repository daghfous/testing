import { AbilityBuilder, MongoAbility } from '@casl/ability'
import abilitiesUtils from '@ateme/login-service/src/services/abilities/utils'

import usersConstants from '../constants/usersConstants'
import { IUnknownObjectKeys } from '@interfaces/Interfaces'
/**
 * @description Build users rules
 * @param {IUnknownObjectKeys} access - user access
 * @param {AbilityBuilder<MongoAbility>} abilityBuilder - casl builder to build accesses
 */
export const buildUsersRules = (access: IUnknownObjectKeys, abilityBuilder: AbilityBuilder<MongoAbility>) => {
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, usersConstants.USERS)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, usersConstants.USERS_RIGHTS)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, usersConstants.USERS_ADD)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, usersConstants.USERS_REMOVE)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, usersConstants.LOGIN)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, usersConstants.ADMIN_GET)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, usersConstants.CREATE_ADMIN_USER)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, usersConstants.REMOVE_USER_BY_NAME)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, usersConstants.GET_USER_BY_NAME)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, usersConstants.UPDATE_USER_BY_NAME)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, usersConstants.FORCE_USER_DISCONNECTION)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, usersConstants.GET_CURRENT_USER)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, usersConstants.GET_CURRENT_USER_ACTIONS)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, usersConstants.REACTIVATE_USER_BY_NAME)
}
