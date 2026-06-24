import { buildIdPRules } from './idp'
import { buildRolesRules } from './roles'
import { buildUsersRules } from './users'
// All build rules.
export const projectRules = [buildIdPRules, buildRolesRules, buildUsersRules]
