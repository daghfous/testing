import { AbilityBuilder, type MongoAbility } from '@casl/ability'
import get from 'lodash/get.js'

import { RIGHTS, UserRightEnum } from './constants/common'
import { IUnknownObjectKeys } from '../../interfaces/Interfaces'

const { VIEW, EDIT, UNSET, HIDDEN, USE } = UserRightEnum

const NOT_HIDDEN = [VIEW, EDIT, UNSET, USE]

const ALL_EDIT = [EDIT, USE]

/**
 * Add weight of right.
 */
const weightRight: Record<UserRightType, number> = {
  [HIDDEN]: 0,
  [UNSET]: 0,
  [VIEW]: 1,
  [USE]: 2,
  [EDIT]: 2
}

export type UserRightType = (typeof UserRightEnum)[keyof typeof UserRightEnum]

type UserRights = Record<string, UserRightType>

/**
 * @description Test if value under path is an object.
 * @param {object} access - Tree
 * @param {string} path - Path value.
 * @returns {boolean} - <true> is node, <false> is leaf
 */
export const isObject = (access: object, path: string) => {
  return typeof get(access, path) === 'object'
}

/**
 * @description Check access is not hidden
 * @param {object} access - user access
 * @param {string} path - path
 * @returns {boolean} - true if not hidden, false otherwise
 */
export const notHidden = (access: object, path: string) => {
  const value = get(access, `${path}.${RIGHTS}`)
  if (isObject(access, path)) return typeof value === 'string' && NOT_HIDDEN.includes(value)
  return NOT_HIDDEN.includes(get(access, path))
}

/**
 * @description Check access is edit
 * @param {object} access - user access
 * @param {string} path - path
 * @returns {boolean} - true if edit, false otherwise
 */
export const isEdit = (access: object, path: string) => {
  const value = get(access, `${path}.${RIGHTS}`)
  if (isObject(access, path)) return typeof value === 'string' && ALL_EDIT.includes(value)
  return ALL_EDIT.includes(get(access, path))
}

/**
 * @description Build right of edit and view
 * @param {object} access - user access
 * @param {AbilityBuilder} abilityBuilder - casl ability builder
 * @param {string} path - path
 * @returns {string} - right on the path
 */
export const buildViewAndUseRight = (access: object, abilityBuilder: AbilityBuilder<MongoAbility>, path: string) => {
  if (!access || !abilityBuilder || !path) return HIDDEN
  const { can } = abilityBuilder

  if (notHidden(access, path)) {
    can(VIEW, path)
    if (isEdit(access, path)) {
      can(USE, path)
      return EDIT
    }
    return VIEW
  }
  return HIDDEN
}

/**
 * Allow to reset all rights by a specific value.
 * @param {object} rightsObject - List of rights to reset.
 * @param {Promise} updateFn - Function to reset values.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const commonRightsSetToChosenLevel = (rightsObject: IUnknownObjectKeys, updateFn: (value: any) => any) => {
  for (const key in rightsObject) {
    if (typeof rightsObject[key] === 'string') {
      rightsObject[key] = updateFn(rightsObject[key])
    } else if (typeof rightsObject[key] === 'object' && rightsObject[key] !== null) {
      commonRightsSetToChosenLevel(rightsObject[key], updateFn)
    }
  }
}

/**
 * Update right of abilities.
 * @param {object} userRights - Tree.
 * @param {string} path - Action path.
 * @param {UserRightEnum} right - Enum.
 * @returns {object} - update userRights tree.
 */
export const setAbilities = (userRights: UserRights, path: string, right: UserRightType): IUnknownObjectKeys => {
  const value: UserRightType = userRights.path || HIDDEN
  const lastWeight = weightRight[value]
  const newWeight = weightRight[right]

  if (lastWeight < newWeight) userRights[path] = right
  return userRights
}

export default {
  buildViewAndUseRight
}
