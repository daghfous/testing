import { useAbility } from '@casl/vue'
import { computed, ComputedRef } from 'vue'

import { USE_RIGHT, VIEW_RIGHT } from '@ateme/login-service/src/services/abilities/constants/common'
import usersConstants from '../constants/usersConstants'

// Create a single instance of the ability
/**
 * @returns {object} - the permissions utils
 */
export default function useUserPermissions() {
  const { can } = useAbility()
  // Create a function to generate computed properties
  const createPermissionComputed = (action: string, subject: string): ComputedRef<boolean> => {
    return computed(() => can(action, subject))
  }
  // Define your computed properties
  const canViewUsers = createPermissionComputed(VIEW_RIGHT, usersConstants.USERS)
  const canAddUsers = createPermissionComputed(USE_RIGHT, usersConstants.USERS_ADD)
  const canRemoveUsers = createPermissionComputed(USE_RIGHT, usersConstants.USERS_REMOVE)
  const canEditUsers = createPermissionComputed(USE_RIGHT, usersConstants.USERS_EDIT)
  const canViewAdmin = createPermissionComputed(VIEW_RIGHT, usersConstants.ADMIN_GET)
  const canUseCreateAdminUser = createPermissionComputed(USE_RIGHT, usersConstants.CREATE_ADMIN_USER)
  const canUseRemoveUserByName = createPermissionComputed(USE_RIGHT, usersConstants.REMOVE_USER_BY_NAME)
  const canViewUserByName = createPermissionComputed(VIEW_RIGHT, usersConstants.GET_USER_BY_NAME)
  const canUseUpdateUserByName = createPermissionComputed(USE_RIGHT, usersConstants.UPDATE_USER_BY_NAME)
  const canUseForceUserDisconnection = createPermissionComputed(USE_RIGHT, usersConstants.FORCE_USER_DISCONNECTION)
  const canViewCurrentUser = createPermissionComputed(VIEW_RIGHT, usersConstants.GET_CURRENT_USER)
  const canViewCurrentUserActions = createPermissionComputed(VIEW_RIGHT, usersConstants.GET_CURRENT_USER_ACTIONS)

  return {
    canViewUsers,
    canAddUsers,
    canRemoveUsers,
    canEditUsers,
    canViewAdmin,
    canUseCreateAdminUser,
    canUseRemoveUserByName,
    canViewUserByName,
    canUseUpdateUserByName,
    canUseForceUserDisconnection,
    canViewCurrentUser,
    canViewCurrentUserActions
  }
}
