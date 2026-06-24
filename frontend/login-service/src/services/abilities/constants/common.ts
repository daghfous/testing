export const API: string = 'API'
export const ALL: string = 'all'

/** All possibility of user rights possibilities in backend */
export const UserRightEnum = Object.freeze({
  HIDDEN: 'hidden',
  UNSET: 'unset',
  VIEW: 'view',
  EDIT: 'edit',
  USE: 'use'
})

export const NOT_HIDDEN: string[] = [UserRightEnum.VIEW, UserRightEnum.EDIT, UserRightEnum.UNSET, UserRightEnum.USE]
export const USE_RIGHT: string = UserRightEnum.USE
export const VIEW_RIGHT: string = UserRightEnum.VIEW

// Common path.
export const ADD: string = 'add'
export const REMOVE: string = 'remove'
export const EDIT: string = 'edit'
export const RIGHTS: string = 'rights'
