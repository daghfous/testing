import { isStandaloneMode } from './constants.ts'

/**
 * Returns the base path of the application.
 * If in appliance mode, it returns "/"
 * Else it returns the first part of the current URL path.
 * @returns {string} - The base path of the application.
 */
export const getTrueBasePath = (): string => {
  if (isStandaloneMode) {
    return '/'
  } else {
    return `${location.pathname.split('/')[1]}/`
  }
}
