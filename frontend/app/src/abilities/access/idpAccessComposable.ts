import { useAbility } from '@casl/vue'
import { computed, ComputedRef } from 'vue'

import { USE_RIGHT, VIEW_RIGHT } from '@ateme/login-service/src/services/abilities/constants/common'
import idpConstants from '../constants/idpConstants'

// Create a single instance of the ability
/**
 * @returns {object} - the idp composable utils
 */
export default function useIdPPermissions() {
  // Create a single instance of the ability

  const { can } = useAbility()
  // Create a function to generate computed properties
  const createPermissionComputed = (action: string, subject: string): ComputedRef<boolean> => {
    return computed(() => can(action, subject))
  }
  const canViewIdP = createPermissionComputed(VIEW_RIGHT, idpConstants.IDP)
  const canAddIdP = createPermissionComputed(USE_RIGHT, idpConstants.IDP_ADD)
  const canRemoveIdP = createPermissionComputed(USE_RIGHT, idpConstants.IDP_REMOVE)
  const canEditIdP = createPermissionComputed(USE_RIGHT, idpConstants.IDP_EDIT)
  const canUseValidateIDP = createPermissionComputed(USE_RIGHT, idpConstants.VALIDATE_IDP) // TODO: TO USE
  const canViewIDPConfigByDomain = createPermissionComputed(VIEW_RIGHT, idpConstants.GET_IDP_CONFIG_BY_DOMAIN) // TODO: TO USE or TO DELETE

  return {
    canViewIdP,
    canAddIdP,
    canRemoveIdP,
    canEditIdP,
    canUseValidateIDP,
    canViewIDPConfigByDomain
  }
}
