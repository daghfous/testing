import ApplicationService from '@ateme/cathodic-ui/src/services/ApplicationService'
import { Ability } from '@casl/ability'
import { abilitiesPlugin } from '@casl/vue'
import cloneDeep from 'lodash/cloneDeep.js'

import { getSingletonBuilder } from './AbilityBuilderRules'
import { defaultRules } from './defaultRules'
import defaultRights from './tree/defaultRights'
import defaultTree from './tree/defaultTreeUpdate'
import { IRoleAction, IUnknownObjectKeys, IUserRights } from '../../interfaces/Interfaces'
import CurrentUserService from '../../services/CurrentUserService'

/**
 * @description Initialization of user right access
 * @param {object} options - List of custom project right
 * @param {object} options.projectTree - List of custom project tree
 * @param {object} options.projectRight - List of custom project right
 * @param {Array} options.projectBuilders - List of custom project builders
 * @param {boolean} options.noAuth - Is there no auth
 * @param {Ability} options.ability - ability update function
 */
export const buildUserRights = async ({
  projectRight = {},
  projectTree = {},
  projectBuilders = [],
  ability,
  noAuth = false
}: IUserRights) => {
  // get all user actions
  // get defined user rights
  const rightsObject: IUnknownObjectKeys = cloneDeep({ ...defaultRights, ...projectRight })
  // get tree object
  const treeObject: IUnknownObjectKeys = { ...defaultTree, ...projectTree }

  if (!noAuth) {
    await CurrentUserService.fillUserActions()
  }
  const actions: IRoleAction[] = CurrentUserService.getCurrentUserActions()

  // update the tree according to the user's actions
  actions.forEach(right => {
    const userAction = right.action as string
    const findTreeUpdate = treeObject[userAction]
    if (findTreeUpdate) findTreeUpdate(rightsObject)
  })

  /* eslint-disable  @typescript-eslint/no-explicit-any */
  const rulesBuilders = defaultRules.concat(projectBuilders as any[])
  getSingletonBuilder().setUserRight(rightsObject, rulesBuilders)
  if (ability) {
    ability.update(getSingletonBuilder().getRules())
  }
}
/**
 * @description Initialization of cast plugin
 */
export const mainDefine = () => {
  ApplicationService.getApp()?.use(abilitiesPlugin, new Ability(getSingletonBuilder().getRules()), {
    useGlobalProperties: true
  })
}
