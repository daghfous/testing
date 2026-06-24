import { preferencesLink } from '../../components/preferences/router'
import { IUnknownObjectKeys } from '@interfaces/Interfaces'
const PATHUSERS: string = 'users'
const NAMEUSERS: string = 'Users'
const PATHROLES: string = 'roles'
const NAMEROLES: string = 'Roles'
const PATHIDPS: string = 'idp'
const NAMEIDPS: string = 'IdPs'
const PATHSESSIONS = 'sessions'
const NAMESESSIONS = 'Active sessions'
/**
 * Link is used to be displayed (somewhere) and to navigate over the route.
 */
export const userLink = {
  path: PATHUSERS,
  name: NAMEUSERS,
  icon: 'users'
}
/**
 * Link is used to be displayed (somewhere) and to navigate over the route.
 */
export const roleLink = {
  path: PATHROLES,
  name: NAMEROLES,
  icon: 'sitemap'
}
/**
 * Link is used to be displayed (somewhere) and to navigate over the route.
 */
export const idpLink = {
  path: PATHIDPS,
  name: NAMEIDPS,
  icon: 'address book outline'
}

/**
 * Link is used to be displayed (somewhere) and to navigate over the route.
 */
export const sessionsLink = {
  path: PATHSESSIONS,
  name: NAMESESSIONS,
  icon: 'address card outline'
}

export const tabs: IUnknownObjectKeys[] = [userLink, roleLink, idpLink, sessionsLink]
export const bottomLinks: IUnknownObjectKeys[] = [preferencesLink]
