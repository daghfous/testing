import { AbilityBuilder, MongoAbility } from '@casl/ability'
import abilitiesUtils from '@ateme/login-service/src/services/abilities/utils'

import rolesConstants from '../constants/rolesConstants'
import { IUnknownObjectKeys } from '@interfaces/Interfaces'
/**
 * @description Build users rules
 * @param {IUnknownObjectKeys} access - user access
 * @param {AbilityBuilder<MongoAbility>} abilityBuilder - casl builder to build accesses
 */
export const buildRolesRules = (access: IUnknownObjectKeys, abilityBuilder: AbilityBuilder<MongoAbility>) => {
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, rolesConstants.ROLES)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, rolesConstants.ROLES_RIGHTS)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, rolesConstants.ROLES_ADD)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, rolesConstants.ROLES_EDIT)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, rolesConstants.ROLES_REMOVE)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, rolesConstants.REMOVE_ROLE_BY_ID)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, rolesConstants.GET_ROLE_BY_ID)
}
