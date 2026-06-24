import { AbilityBuilder, MongoAbility } from '@casl/ability'

import globalConstants from './constants'
import abilitiesUtils from './utils'
import { IUnknownObjectKeys } from '../../interfaces/Interfaces'
/**
 * @description Build users rules
 * @param {IUnknownObjectKeys} access - user access
 * @param {IUnknownObjectKeys} abilityBuilder - casl builder to build accesses
 */
const buildCommonRules = (access: IUnknownObjectKeys, abilityBuilder: AbilityBuilder<MongoAbility>) => {
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, globalConstants.GET_DEF)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, globalConstants.GET_DOC)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, globalConstants.GET_PING)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, globalConstants.ACTIONS_GET)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, globalConstants.POST_API_DEFINITION)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, globalConstants.GET_CONFIGURATION)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, globalConstants.UPDATE_CONFIGURATION)

  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, globalConstants.REFRESH_TOKEN)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, globalConstants.TOKEN_INTROSPECTION)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, globalConstants.CHANGE_TOKEN_EXPIRATION)

  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, globalConstants.CHANGE_PASSWORD)
  abilitiesUtils.buildViewAndUseRight(access, abilityBuilder, globalConstants.LOGOUT)
}

export const defaultRules = [buildCommonRules]
