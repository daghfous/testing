import axios, { AxiosHeaders, AxiosInstance, CreateAxiosDefaults } from 'axios'

import tokenService from '../services/TokenService'

const userRootPath: string = process.env.USER_MANAGEMENT_URL || 'users/'

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

export const TIMEOUT: number = 5000
export const LOGIN_TIMEOUT: number = 10000
export const usersClient: AxiosInstance = createClient(userRootPath)
