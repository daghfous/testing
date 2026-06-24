import axios from 'axios'

import TokenService from '../services/TokenService'

axios.interceptors.response.use(
  response => response,
  TokenService.tokenErrorInterceptorsBuilder(TokenService.errorTokenCallback(axios))
)

export default axios
