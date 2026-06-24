import { useAbility } from '@casl/vue'
import { computed, ComputedRef } from 'vue'

import { USE_RIGHT, VIEW_RIGHT } from '@ateme/login-service/src/services/abilities/constants/common'
import rolesConstants from '../constants/rolesConstants'

// Create a single instance of the ability
/**
 * @returns {object} - the role composable utils
 */
export default function useRolePermissions() {
  const { can } = useAbility()
  // Create a function to generate computed properties
  const createPermissionComputed = (action: string, subject: string): ComputedRef<boolean> => {
    return computed(() => can(action, subject))
  }
  const canViewRoles = createPermissionComputed(VIEW_RIGHT, rolesConstants.ROLES)
  const canAddRoles = createPermissionComputed(USE_RIGHT, rolesConstants.ROLES_ADD)
  const canRemoveRoles = createPermissionComputed(USE_RIGHT, rolesConstants.ROLES_REMOVE)
  const canEditRoles = createPermissionComputed(USE_RIGHT, rolesConstants.ROLES_EDIT)

  return {
    canViewRoles,
    canAddRoles,
    canRemoveRoles,
    canEditRoles
  }
}
