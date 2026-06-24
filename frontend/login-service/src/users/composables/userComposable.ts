import { storeToRefs } from 'pinia'
import { ref } from 'vue'

import { authenticateModeStore, IAuthenticateMode } from '../../auth/store/authenticateMode'
import { ISelectInputOption } from '../../interfaces/Interfaces'

// #####################################
// STORE
// #####################################
export const useAuthenticateMode = () => {
  const { getAuthenticateMode } = storeToRefs(authenticateModeStore())
  return { getAuthenticateMode }
}

// #####################################
// DATA
// #####################################
export const initialized = ref<boolean>(false)

// #####################################
// METHODS
// #####################################
/**
 * get IDp object from idp_name
 * @param {string} idp_name - the name of the identity provider
 * @returns {object} - the complete identity provider
 */
export const getIdpFromIdpName = (idp_name: string): IAuthenticateMode | undefined => {
  return authenticationModes().find(mode => (mode.idp_name as string) === idp_name)
}

/**
 * Is user a LDAP one?
 * @param {string} idp_name - idp_name
 * @returns {boolean} - <true> if LDAP
 */
export const isLdapUser = (idp_name: string): boolean => {
  const idp = idp_name || 'local'
  const idpObject = getIdpFromIdpName(idp)
  return idpObject ? idpObject.idp_type === 'ldap' : false
}

/**
 * Is user a SAML one?
 * @param {string} idp_name - idp_name
 * @returns {boolean} - <true> if SAML
 */
export const isSamlUser = (idp_name: string): boolean => {
  const idp = idp_name || 'local'
  const idpObject = getIdpFromIdpName(idp)
  return idpObject ? idpObject.idp_type === 'saml' : false
}

/**
 * List all authentication mode available.
 * @returns {Array} - List of authentication mode.
 */
export const authenticationModes = (): IAuthenticateMode[] => {
  return Array.isArray(authenticateModeStore().getAuthenticateMode)
    ? (authenticateModeStore().getAuthenticateMode as unknown as IAuthenticateMode[])
    : []
}

/**
 * Parse authenticate modes for select.
 * @returns {Array<ISelectInputOption>} - List of authentication modes.
 */
export const readableAuthenticateModes = (): ISelectInputOption[] => {
  return authenticationModes().map((mode: IAuthenticateMode) => ({
    label: mode.idp_label as string,
    value: mode.idp_name as string
  }))
}

export default {
  initialized,
  getIdpFromIdpName,
  isLdapUser,
  isSamlUser,
  authenticationModes,
  readableAuthenticateModes
}
