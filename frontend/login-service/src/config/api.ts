import axios, { AxiosHeaders, AxiosInstance, CreateAxiosDefaults } from 'axios'

import tokenService from '../services/TokenService'
import EnvService from '@ateme/cathodic-ui/src/services/EnvService.ts'

// base config for axios clients
const clientConfig = {
  headers: {
    'Content-Type': 'application/json'
  },
  /* Redefine sessionToken at each call, to avoid using the previous sessionToken,
     or undefined value because client is created before sessionToken was created
  */
  transformRequest: [
    (data: unknown, headers: AxiosHeaders) => {
      headers.set('Authorization', tokenService.sessionToken)
      return data
    },
    ...((axios.defaults.transformRequest as unknown[]) || [])
  ]
}

/**
 * Axios Client with interceptor
 * @param {string} path - baseUrl for axios calls
 * @returns {AxiosInstance} Axios instance for making requests
 */
const createClient = (path: string): AxiosInstance => {
  return axios.create({ baseURL: path, ...clientConfig } as CreateAxiosDefaults)
}

// Export constants
export const TIMEOUT: number = 5000
export const LOGIN_TIMEOUT: number = 10000

// Export createClient for dynamic client creation
export { createClient }

// usersClient will be created after EnvService is initialized
// This is a getter function to ensure it's created with the correct env values
let usersClientInstance: AxiosInstance | null = null
export const getUsersClient = (): AxiosInstance => {
  if (!usersClientInstance) {
    const userRootPath = EnvService.getInstance().getEnv('USER_MANAGEMENT_URL') || 'users/'
    usersClientInstance = createClient(userRootPath)
  }
  return usersClientInstance
}

// For backward compatibility, export usersClient as a getter
// Note: This will be initialized on first use
export const usersClient: AxiosInstance = getUsersClient()
