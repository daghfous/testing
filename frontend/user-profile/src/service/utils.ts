import { UserProfileElement } from '../interfaces/userProfile'
import Logger from '@ateme/cathodic-ui/src/services/Logger'

/**
 * Waits for the UserProfile DOM element to be available.
 * @returns {Promise<UserProfileElement>} - Promise resolving to the found element
 * @param {string} selector - CSS selector of the element to wait for
 * @param {number} [timeout] - Maximum time to wait in milliseconds
 * @private
 * @throws {Error} If the element is not found within the timeout period
 */
export const waitForElement = (selector: string, timeout: number = 1000): Promise<UserProfileElement> => {
  return new Promise((resolve, reject) => {
    const interval = 100 // in milliseconds
    let elapsed = 0

    const check = () => {
      const element = document.querySelector(selector) as UserProfileElement
      if (element) {
        resolve(element)
      } else if (elapsed >= timeout) {
        Logger.debug('user-profile service/utils.ts > waitForElement', `Timeout waiting for ${selector}`)
        reject(new Error(`${selector} element not found in DOM.`))
      } else {
        elapsed += interval
        setTimeout(check, interval)
      }
    }
    check()
  })
}
