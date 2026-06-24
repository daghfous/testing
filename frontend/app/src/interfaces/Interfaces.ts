export enum ERoleMode {
  basic = 'basic',
  expert = 'expert'
}
export interface IUnknownObjectKeys {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any
}

export interface INotifyLabel {
  pending: string
  resolved: string
  rejected: string
}

export interface IIdpMapper {
  _id?: string
  type?: string
  attribute_name?: string
  attribute_value?: string
  attributes?: IAttributes[]
  scopes_to_add?: string[]
  roles_to_add?: string[]
}
export interface IAttributes {
  name?: string
  value?: string
}
export interface IIdp extends Partial<ILdapIdp>, Partial<ISamlIdp> {
  idp_type?: string
  idp_name?: string
  idp_label?: string
  scopes?: string[]
  roles?: string[]
  mappers?: IIdpMapper[]
  roles_updated?: boolean
  deny_access?: boolean
  username?: string
  password?: string
}

export interface ILdapIdp {
  server?: string
  domain?: string
  search?: string
  search_filter?: string
  group?: string
  automatically_add_user?: boolean
  use_ssl?: boolean
  bind_dn?: string
  bind_password?: string
  user_filter?: string
}
export interface ISamlIdp {
  entity_id?: string
  single_sign_on_service?: string
  single_logout_service?: string
  cert_fingerprint?: string
  sign_authn_request?: boolean
  sign_logout_request?: boolean
  sp_public_cert?: string
  sp_private_cert?: string
}

export interface IRole {
  id?: string
  label?: string
  content?: IRoleAction[] | IRole[]
  role_unicity_key?: string
  default?: boolean
  title?: string
  description?: string
  scope?: string
}

export interface IBackendPaginatedQuery {
  sort?: string
  range?: string
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
