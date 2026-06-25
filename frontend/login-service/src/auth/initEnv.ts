import EnvService from '@ateme/cathodic-ui/src/services/EnvService'
import Logger from '@ateme/cathodic-ui/src/services/Logger'

// Initialize EnvService immediately when this module is imported
// This ensures that initConfigMap() is called before any getEnv() calls
EnvService.getInstance().initConfigMap().then((success) => {
  if (success) {
    Logger.debug('login-service/initEnv', 'Environment configuration loaded from ConfigMap successfully')
  } else {
    Logger.warn('login-service/initEnv', 'Failed to load environment configuration from ConfigMap, falling back to defaults')
  }
}).catch((error) => {
  Logger.error('login-service/initEnv', `Error loading environment configuration: ${error}`)
})

// Export empty object to ensure module execution
export {}
