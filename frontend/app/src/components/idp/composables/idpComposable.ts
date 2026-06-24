import { type StoreGeneric, storeToRefs } from 'pinia'
import { computed, Ref, ref, watch } from 'vue'

import { IIdp, IIdpMapper, IRole } from '@interfaces/Interfaces'
import { idpStore, rolesStore } from '@store/allStoreDefinition'
import { loginServiceStore } from '@store/loginServiceStore'

/**
 *
 * @param {string} idpName - the idp name
 * @param {boolean} createMode - is this in creation mode
 * @param {IIdpMapper} selectedMapper - the selected idp mapper
 * @returns {object} - all the idp composable utils
 */
export function useIdpManagement(idpName?: string, createMode?: boolean, selectedMapper?: string) {
  const { getIdPs } = storeToRefs(idpStore()) as unknown as {
    getIdPs: Ref<IIdp[]>
  }
  const { getAllRoles } = storeToRefs(rolesStore()) as unknown as {
    getAllRoles: Ref<IRole[]>
  }
  const { getIsAdmin } = storeToRefs(loginServiceStore() as StoreGeneric)

  const fakePassword = ref<string>('zZ!0zzzzZ!0zzz')
  const idpModel = ref<IIdp>({})
  const idpMapperModel = ref<IIdpMapper>({})

  const isConnectedUserAdmin = computed((): boolean => getIsAdmin.value)
  /**
   * List all available roles.
   * @returns {Array} - Array of available roles.
   */
  const existingRoles = computed((): string[] => {
    return getAllRoles.value.map((role: IRole) => role.id as string)
  })
  const idpCurrent = computed((): IIdp => getIdPs.value.find((idp: IIdp) => idp.idp_name === idpName) ?? {})

  const isLdapIdP = computed((): boolean => idpCurrent.value?.idp_type === 'ldap')
  const isSamlIdP = computed((): boolean => idpCurrent.value?.idp_type === 'saml')
  const isLdapIdPModel = computed((): boolean => idpModel.value?.idp_type === 'ldap')
  const isSamlIdPModel = computed((): boolean => idpModel.value?.idp_type === 'saml')

  /**
   *
   * @param {IIdp} model - the idp model
   * @param {IIdp} current - the current idp
   */
  function assignIdpModel(model: IIdp, current: IIdp) {
    Object.assign(model, current)
    if (current?.bind_dn && !createMode) {
      model.bind_password = fakePassword.value
      current.bind_password = fakePassword.value
    }
    if (model?.sign_logout_request === undefined && model?.idp_type === 'saml') {
      model.sign_logout_request = !!(model.sp_public_cert || model.sp_private_cert)
      current.sign_logout_request = !!(current.sp_public_cert || current.sp_private_cert)
    }
  }

  /**
   *
   * @param {string} id - the id
   * @returns {string} - the role label
   */
  function getRoleLabel(id: string) {
    const role = getAllRoles.value.find(s => s.id === id)
    return role ? role.title : id
  }

  watch(
    idpCurrent,
    newValue => {
      assignIdpModel(idpModel.value, newValue)
    },
    { deep: true, immediate: true }
  )

  return {
    fakePassword,
    idpModel,
    idpMapperModel,
    isConnectedUserAdmin,
    isLdapIdP,
    isLdapIdPModel,
    isSamlIdP,
    isSamlIdPModel,
    existingRoles,
    idpCurrent,
    getRoleLabel,
    selectedMapper
  }
}
