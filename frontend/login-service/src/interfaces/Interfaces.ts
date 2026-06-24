import { AxiosResponse } from 'axios'

export interface IUnknownObjectKeys {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any
}

/**
 * User Interface
 */
export interface IUser {
  username?: string
  password?: string
  login?: string
  idp_name?: string
  mode?: string
  domain?: string
  level?: string | number
  oldPassword?: string
  newPassword?: string
  roles: string[]
  scopes?: string[]
  first_login?: string | boolean
  user_unicity_key?: string // Concatenation of ${username},${idp_name} (needed only for table)
  password_expired?: string
  user_id?: string
  confirmPassword?: string
  preferences?: object
  session_timeout_disabled?: boolean
  password_expiration_disabled?: boolean
  password_expiration_changed?: boolean
  submit?: string
  duplicate?: boolean
  session_timeout_changed?: boolean
  idp_type?: string
}

export type IUserError = {
  [K in keyof IUser]?: string
}

interface SchemaProperty {
  pattern?: string
  [key: string]: string | undefined
}

export interface Schema {
  properties: {
    [key: string]: SchemaProperty
  }
  required: string[]
}

export interface RequestClient {
  request(config: unknown): Promise<AxiosResponse>
}

export interface AxiosErrorResponse {
  message: string
}

export interface ISelectInputOption {
  label: string
  value: string
}

export interface IRoleAction {
  id?: string
  action?: string
  policy?: string
  resource?: IUnknownObjectKeys
  role?: string
  label?: string
  title?: string
  description?: string
  scope?: string
  prefix?: string
  name?: string
}

export interface IUserRights {
  projectRight?: IUnknownObjectKeys
  projectTree?: IUnknownObjectKeys
  projectBuilders?: IUnknownObjectKeys[]
  ability?: IUnknownObjectKeys
  noAuth?: boolean
}

export interface IPasswordPolicy {
  regex_pattern?: string
  expiration_delay_in_days?: number
  password_min_length?: number
}

export interface ITimeoutConfiguration {
  force_change_password: boolean
  refresh_token_expiration: number | string // Can be string for select input options
  token_expiration?: number
  logout_timeout: number | string // Can be string for select input options
  user_deactivation_period: number
  max_successive_failed_login: number
  password_policy: IPasswordPolicy
}

export interface TrackUserActionsOptions {
  inactivityTimeout?: number
  debounceTimeout?: number
  inactiveUserAction?: (() => void) | null
}
