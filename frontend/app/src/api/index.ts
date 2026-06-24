import tokenService from '@ateme/login-service/src/services/TokenService'
import ApiClientService from '@ateme/cathodic-ui/src/services/ApiClientService'
import { getEnv } from '@ateme/cathodic-ui/src/utils/EnvUtils'

export const initializeApiClient = async () => {
  if (!getEnv('VITE_USER_MANAGEMENT_URL')) return

  const apiClient: ApiClientService = ApiClientService.getInstance()
  apiClient.registerGlobalFunction(
    (config: RequestInit) => config,
    (response: Response) => Promise.resolve(response),
    () => tokenService.sessionToken,
    (response: Response) => Promise.resolve(response.ok)
  )
}
