import { AbilityBuilder, MongoAbility } from '@casl/ability'
import abilitiesUtils from '@ateme/login-service/src/services/abilities/utils'

import idpConstants from '../constants/idpConstants'
import { IUnknownObjectKeys } from '@interfaces/Interfaces'
/**
 * @description Build users rules
 * @param {IUnknownObjectKeys} access - user access
 * @param {AbilityBuilder<MongoAbility>} abilityBuilder - casl builder to build accesses
 */
export const buildIdPRules = (access: IUnknownObjectKeys, abilityBuilder: AbilityBuilder<MongoAbility>) => {
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, idpConstants.IDP)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, idpConstants.IDP_ADD)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, idpConstants.IDP_RIGHTS)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, idpConstants.IDP_EDIT)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, idpConstants.IDP_REMOVE)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, idpConstants.GET_IDP_CONFIG_BY_DOMAIN)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, idpConstants.VALIDATE_IDP)
}
