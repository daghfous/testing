import '@ateme/cathodic-ui/assets-cathodic-ui/style/inject.scss'
import initializeLogin from '@ateme/login-service/src/auth/initializeLogin.ts'
import Logger from '@ateme/cathodic-ui/src/services/Logger'
import { UserProfileService } from './service'

const userProfileService = new UserProfileService()


/**
 * Starts the login initialization process with specified configurations.
 * This includes setting the language locale, login options, product logo, project name, and the project initialization function.
 */
if (import.meta.env.DEV) {
  Logger.debug('user-profile main.ts', 'Starting in DEV mode via initializeLogin.start')
  initializeLogin.start({
    app: {},
    productLoginLogo: '',
    langLocale: 'en-US',
    optionsLogin: {
      defaultAdminLevel: null
    },
    projectName: 'User Profile',
    projectInitialize: () => {
      Logger.debug('user-profile main.ts > projectInitialize', 'Initializing user-profile service and unmounting login')
      return [
        userProfileService.init(),
        initializeLogin.unmount()
      ]
    }
  })
} else {
  Logger.debug('user-profile main.ts', 'Starting in non-DEV mode')
  userProfileService.init()
}
