import { type StoreGeneric, storeToRefs } from 'pinia'
import { computed, ref } from 'vue'
import { useTranslation } from 'i18next-vue'

import { useAuthenticateModeStore } from '@store/authenticateModeStore'
import { ISelectInputOption } from '@ateme/login-service/src/interfaces/Interfaces'
import schema from '@ateme/login-service/src/users/config/UserInput.json'
import { IIdp, IUnknownObjectKeys } from '@interfaces/Interfaces'
import { loginServiceStore } from '@store/loginServiceStore'
import { configurationsStore } from '../../../components/preferences/store'

/**
 * @returns {object} - All the users composable utils
 */
export function useUsersManagement() {
  // #####################################
  // INJECT
  // #####################################
  const { t } = useTranslation()

  // -------------------
  // store
  // -------------------
  const store = loginServiceStore() as StoreGeneric
  const { getIsAdmin } = storeToRefs(store)
  const confStore = configurationsStore()
  const { getData } = storeToRefs(confStore)

  // #####################################
  // DATA
  // #####################################
  const fakePassword = ref<string>('zZ!0zzzzZ!0zzz')
  // #####################################
  // COMPUTED
  // #####################################
  const isCurrentUserAdmin = computed((): boolean => {
    return getIsAdmin.value
  })
  const userSchema = computed((): IUnknownObjectKeys => {
    const updatedSchema = JSON.parse(JSON.stringify(schema))
    const pattern = getData.value.password_policy?.regex_pattern

    const minLength = getData.value.password_policy?.password_min_length
    // Update pattern
    updatedSchema['properties']['password']['pattern'] = pattern?.replace('{,255}', `{${minLength},255}`)
    // Update description
    updatedSchema['properties']['password']['description'] = `${t('users.main.create.updatePwdWarning')}${t(
      'users.inputs.password.description',
      {
        min_length: minLength
      }
    )}`
    return updatedSchema
  })
  // #####################################
  // METHODS
  // #####################################
  /**
   * List all authentication mode available.
   * @returns {Array} - List of authentication mode.
   */
  const authenticationModes = computed((): IIdp[] => {
    return Array.isArray(useAuthenticateModeStore().getAuthenticateMode)
      ? (useAuthenticateModeStore().getAuthenticateMode as unknown as IIdp[])
      : []
  })
  /**
   * Parse authenticate modes for select.
   * @returns {Array<ISelectInputOption>} - List of authentication modes.
   */
  const readableAuthenticateModes = computed((): ISelectInputOption[] => {
    return authenticationModes.value.map((mode: IIdp) => ({
      label: mode.idp_label as string,
      value: mode.idp_name as string
    }))
  })
  /**
   * get IDp object from idp_name
   * @param {string} idp_name - the name of the identity provider
   * @returns {object} - the complete identity provider
   */
  const getIdpFromIdpName = (idp_name: string): IIdp | undefined => {
    return authenticationModes.value.find((mode: IIdp) => (mode.idp_name as string) === idp_name)
  }
  /**
   * Is user a LDAP one?
   * @param {string} idp_name - idp_name
   * @returns {boolean} - <true> if LDAP
   */
  const isLdapUser = (idp_name: string | undefined): boolean => {
    const idp = idp_name || 'local'
    const idpObject = getIdpFromIdpName(idp)
    return idpObject ? idpObject.idp_type === 'ldap' : false
  }

  /**
   * Is user a SAML one?
   * @param {string} idp_name - idp_name
   * @returns {boolean} - <true> if SAML
   */
  const isSamlUser = (idp_name: string | undefined): boolean => {
    const idp = idp_name || 'local'
    const idpObject = getIdpFromIdpName(idp)
    return idpObject ? idpObject.idp_type === 'saml' : false
  }

  return {
    fakePassword,
    authenticationModes,
    isCurrentUserAdmin,
    userSchema,
    readableAuthenticateModes,
    getIdpFromIdpName,
    isLdapUser,
    isSamlUser
  }
}
