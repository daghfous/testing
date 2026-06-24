<script setup lang="ts">
  import { IEntity } from '@ateme/cathodic-ui/src/interfaces/PageHeader'
  import TemplateView from '@ateme/cathodic-ui/src/components/template/TemplateView.vue'
  import { computed, onMounted, ref, watchEffect } from 'vue'
  import BaseCard from '@ateme/cathodic-ui/src/components/containers/BaseCard.vue'
  import TextInput from '@ateme/cathodic-ui/src/components/inputs/TextInput.vue'
  import PasswordInput from '@ateme/cathodic-ui/src/components/inputs/PasswordInput.vue'
  import BooleanInput from '@ateme/cathodic-ui/src/components/inputs/BooleanInput.vue'
  import SelectInput from '@ateme/cathodic-ui/src/components/inputs/SelectInput.vue'
  import { ISelectInputOption } from '@ateme/cathodic-ui/src/interfaces/SelectInput.ts'
  import type { BreadCrumbsDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/breadCrumbs.d.ts'
  import SeparatorHeader from '@ateme/cathodic-ui/src/components/elements/SeparatorHeader.vue'
  import {
    EIconBorderLayer,
    EIconNotesClipboard,
    EIconOtherDevice,
    EIconSettings,
    EIconTime,
    EIconUploadDownload
  } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
  import { EFileType } from '@ateme/cathodic-ui/src/interfaces/FileManage'
  import DownloadAnchor from '@ateme/cathodic-ui/src/components/elements/DownloadAnchor.vue'
  import type { BaseButtonDef, PromiseButtonDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons.d.ts'
  import { idpLink } from '../router'
  import { useTranslation } from 'i18next-vue'
  import { useRouter } from 'vue-router'
  import { IIdp, IIdpMapper, IUnknownObjectKeys } from '@interfaces/Interfaces.ts'
  import { idpStore } from '../../../components/idp/store'
  import { storeToRefs } from 'pinia'
  import { rolesStore } from '../../../components/roles/store'
  import MappersCard from '../../../components/idp/components/MappersCard.vue'
  import RouteConfirm from '../../common/RouteConfirm.vue'
  import { IUser } from '@ateme/login-service/src/interfaces/Interfaces'
  import { copyClipBoard } from '@ateme/cathodic-ui/src/utils/copyClipboard'
  import BubbleText from '@ateme/cathodic-ui/src/components/elements/BubbleText.vue'
  import { EIconValidations } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum.ts'
  // -------------------
  // i18n
  // -------------------
  const { t } = useTranslation()
  // -------------------
  // Router
  // -------------------
  const router = useRouter()
  // -------------------
  // store
  // -------------------
  const storeIdp = idpStore()
  const { getIdPs } = storeToRefs(storeIdp)
  const { getSpMetadata, fillIdPs, initializeIdP, updateIdP, validateIdP } = idpStore()
  const storeRoles = rolesStore()
  const { fillRoles } = storeRoles
  // -------------------
  // options
  // -------------------
  const langPath: string = 'users.idp'
  export type AddEditIdpProps = {
    idpName?: string
  }

  const props = withDefaults(defineProps<AddEditIdpProps>(), {
    idpName: undefined
  })
  // #####################################
  // HOOK
  // #####################################
  onMounted(async () => {
    loading.value = true
    await fillIdPs()
    await fillRoles()
    await initData()
    await refreshMetadata()
    loading.value = false
  })
  // #####################################
  // DATA
  // #####################################
  const entity = ref<IEntity>(idpLink)
  const currentIdp = ref<IIdp>({
    idp_type: 'ldap',
    deny_access: true,
    use_ssl: false,
    roles: ['all:guest'],
    search_filter: '(objectClass=person)'
  })
  const defaultIdp = ref<IIdp>({
    idp_type: 'ldap',
    deny_access: true,
    use_ssl: false,
    roles: ['all:guest'],
    search_filter: '(objectClass=person)'
  })
  const defaultRoles = ref<string[]>([])
  const defaultMappers = ref<IIdpMapper[]>([])
  const editMode = ref<boolean>(!!props.idpName)
  const idpError = ref<IUnknownObjectKeys>({})
  const currentRoles = ref<string[]>([])
  const currentMappers = ref<IIdpMapper[]>([])
  const loading = ref<boolean>(false)
  const currentUser = ref<Partial<IUser>>({})
  const spMetadata = ref<string | undefined>(undefined)
  const downloadContent = ref<File | undefined>(undefined)
  const mappersCardRef = ref()
  const submitted = ref<boolean>(false)
  const submitButtonLabels: [string, string, string, string] = [
    t('common.save'),
    t('common.saving'),
    t('common.saved'),
    t('common.cantSave')
  ]

  /**
   * @description Button to cancel the role edition/creation, make the user returns to the roles list view
   */
  const cancelButton: BaseButtonDef = {
    icon: EIconValidations.ClearCircle,
    label: t('common.cancel'),
    title: t('common.cancel'),
    eventClick: () => router.push(idpLink.path)
  }
  // #####################################
  // COMPUTED
  // #####################################
  const submitButton = computed((): PromiseButtonDef => {
    return {
      disabled: (hasError.value || disabledSubmitButton.value) as boolean,
      labels: submitButtonLabels,
      title: t('common.save'),
      icon: EIconOtherDevice.Save,
      handler: async () => await validateAndSubmit()
    }
  })

  const testIdpConfigButton = computed((): BaseButtonDef => {
    return {
      icon: EIconBorderLayer.LayerCheck,
      disabled: isLdapIdP.value ? !currentUser.value.username || !currentUser.value.password : false,
      label:
        currentIdp.value.idp_type === 'saml'
          ? t(`${langPath}.template.validateConfig`)
          : t(`${langPath}.template.testServer`),
      eventClick: () => testIdpConfig()
    } as BaseButtonDef
  })

  const refreshMetadataButton = computed((): BaseButtonDef => {
    return {
      id: 'refresh-metadata-button',
      icon: EIconTime.Update,
      disabled: !currentIdp.value.idp_name,
      label: t('users.idp.spMetadata.refreshMetadata'),
      eventClick: () => refreshMetadata()
    } as BaseButtonDef
  })

  /**
   * Detect if there is pending changes in the form.
   * @returns {boolean} - <true> there is pending changes, <false> otherwise.
   */
  const hasPendingChanges = computed((): boolean => {
    return (
      JSON.stringify(normalizeIdp(currentIdp.value)) !== JSON.stringify(normalizeIdp(defaultIdp.value)) &&
      !submitted.value
    )
  })
  /**
   * Disabled value of submit button if required fields aren't set.
   * @returns {boolean} <true> enabled, <false> disabled
   */
  const disabledSubmitButton = computed((): boolean => {
    if (editMode.value) {
      const hasChanged =
        JSON.stringify(currentIdp.value) !== JSON.stringify(defaultIdp.value) ||
        JSON.stringify(currentMappers.value) !== JSON.stringify(defaultMappers.value) ||
        JSON.stringify(currentRoles.value) !== JSON.stringify(defaultRoles.value)
      return !hasChanged
    }
    return currentIdp.value.idp_type === 'ldap'
      ? !currentIdp.value.server ||
          !currentIdp.value.search ||
          !currentIdp.value.idp_name ||
          !currentIdp.value.idp_label ||
          !currentIdp.value.group ||
          (!currentIdp.value.bind_dn && !!currentIdp.value.bind_password) ||
          ((!!currentIdp.value.bind_dn &&
            (!currentIdp.value.bind_password || !currentIdp.value.user_filter)) as boolean)
      : currentIdp.value.idp_type === 'saml'
        ? !currentIdp.value.idp_name ||
          !currentIdp.value.entity_id ||
          !currentIdp.value.single_sign_on_service ||
          !currentIdp.value.single_logout_service ||
          !currentIdp.value.cert_fingerprint ||
          (((currentIdp.value.sign_authn_request || currentIdp.value.sign_logout_request) &&
            (!currentIdp.value.sp_public_cert || !currentIdp.value.sp_private_cert)) as boolean)
        : false
  })

  const hasError = computed((): boolean => {
    if (currentIdp.value) {
      return updateErrorInput()
    }
    return false
  })
  const idpHeaderLabel = computed(() => {
    return editMode.value ? t('common.editWithName', { name: props.idpName }) : t('users.idp.template.headerLabel.add')
  })
  /**
   * List of idp types
   * @returns {Array} Array of select options
   */
  const idpTypes = computed((): ISelectInputOption[] => {
    return [
      { label: 'LDAP', value: 'ldap' },
      { label: 'SAML', value: 'saml' }
    ] as ISelectInputOption[]
  })

  const isLdapIdP = computed(() => {
    return currentIdp.value.idp_type === 'ldap'
  })

  const isSamlIdP = computed(() => {
    return currentIdp.value.idp_type === 'saml'
  })

  const disabledCertificateFields = computed(() => {
    return currentIdp.value.sign_authn_request || currentIdp.value.sign_logout_request
  })
  const redirectUri = computed((): string | undefined | null => {
    if (typeof window !== 'undefined' && 'DOMParser' in window && spMetadata.value) {
      try {
        const parser = new DOMParser()
        const xmlDoc = parser.parseFromString(spMetadata.value, 'text/xml')
        const result: Attr | null = xmlDoc
          .getElementsByTagName('md:AssertionConsumerService')[0]
          .attributes.getNamedItem('Location')
        return result?.nodeValue
      } catch (error) {
        return undefined
      }
    }
    return undefined
  })

  const copyToClipboardButton = computed((): BaseButtonDef => {
    return {
      icon: EIconNotesClipboard.Clipboard1,
      title: t('users.idp.spMetadata.copyToClipboard'),
      label: t('users.idp.spMetadata.copyToClipboard'),
      eventClick: () => copyRedirectUri()
    } as BaseButtonDef
  })

  const downloadSpMetadataButton = computed((): BaseButtonDef => {
    return {
      icon: EIconUploadDownload.Download1,
      label: t('users.idp.spMetadata.downloadSpMetadata'),
      title: t('users.idp.spMetadata.downloadSpMetadata'),
      eventClick: () => downloadSpMetadataFile()
    } as BaseButtonDef
  })
  // #####################################
  // METHODS
  // #####################################

  const refreshMetadata = async () => {
    spMetadata.value = await getSpMetadata(currentIdp.value.idp_name as string)
  }
  const copyRedirectUri = () => {
    copyClipBoard(redirectUri.value || '')
  }
  const downloadSpMetadataFile = () => {
    downloadContent.value = spMetadata.value as unknown as File
  }
  const initData = () => {
    if (props.idpName) {
      currentIdp.value = {
        ...(getIdPs.value.find(idp => idp.idp_name === props.idpName) as IIdp)
      }
      defaultIdp.value = {
        ...(getIdPs.value.find(idp => idp.idp_name === props.idpName) as IIdp)
      }
      currentRoles.value = currentIdp.value.roles ? [...currentIdp.value.roles] : []
      defaultRoles.value = defaultIdp.value.roles ? [...defaultIdp.value.roles] : []
      currentMappers.value = currentIdp.value.mappers ? [...currentIdp.value.mappers] : []
      defaultMappers.value = defaultIdp.value.mappers ? [...defaultIdp.value.mappers] : []
    }
  }
  const breadCrumbs = computed((): BreadCrumbsDef => {
    const elementList = [entity.value.name, idpHeaderLabel.value]
    return {
      id: 'create-update-idp',
      elementList: elementList,
      routerPushHandler: event => {
        // Can only click on deployed apps
        if (event.length === 1) {
          router.push(idpLink.path)
        }
      }
    } as BreadCrumbsDef
  })

  /**
   * Test if there is errors in the form.
   * @returns {boolean} - <true> there is a error, <false> otherwise.
   */
  const updateErrorInput = (): boolean => {
    idpError.value = {}
    if (!currentIdp.value?.idp_name?.match('^[A-Za-z0-9_.-]*$')) {
      idpError.value.idp_name = [t('users.errors.invalidFormat')]
    }
    if (!submitted.value) {
      if (!editMode.value) {
        const existingIdp = getIdPs.value?.find(idp => idp.idp_name === currentIdp.value.idp_name)
        if (existingIdp) {
          idpError.value.idp_name = [
            t(`${langPath}.errors.existingIdp`, {
              idp_name: currentIdp.value.idp_name
            })
          ]
        }
      }
    }
    return Object.keys(idpError.value).length > 0
  }
  /**
   * Normalize an idp object before sending it to the backend.
   * @param {IIdp} idp - The idp to normalize.
   * @returns {IIdp} - The normalized idp.
   */
  const normalizeIdp = (idp: IIdp): IIdp => {
    const normalized: IIdp = {
      idp_type: idp.idp_type,
      idp_name: idp.idp_name,
      idp_label: idp.idp_label,
      scopes: idp.roles,
      deny_access: idp.deny_access,
      roles: idp.roles ? (idp.roles.length > 0 ? idp.roles : ['all:guest']) : ['all:guest'],
      mappers: currentMappers.value
    }

    if (idp.idp_type === 'ldap') {
      normalized.server = idp.server
      normalized.domain = idp.domain
      normalized.search = idp.search
      normalized.group = idp.group
      normalized.automatically_add_user = idp.automatically_add_user
      normalized.use_ssl = idp.use_ssl
      normalized.bind_dn = idp.bind_dn
      normalized.bind_password = idp.bind_password
      normalized.user_filter = idp.user_filter
      normalized.search_filter = idp.search_filter
    }

    if (idp.idp_type === 'saml') {
      normalized.entity_id = idp.entity_id
      normalized.single_sign_on_service = idp.single_sign_on_service
      normalized.single_logout_service = idp.single_logout_service
      normalized.cert_fingerprint = idp.cert_fingerprint
      normalized.deny_access = idp.deny_access
      normalized.sign_authn_request = idp.sign_authn_request
      normalized.sign_logout_request = idp.sign_logout_request

      if (idp.sign_authn_request || idp.sign_logout_request) {
        normalized.sp_public_cert = idp.sp_public_cert
        normalized.sp_private_cert = idp.sp_private_cert
      } else {
        if (editMode.value) {
          normalized.sp_public_cert = ''
          normalized.sp_private_cert = ''
        }
      }
    }

    return normalized
  }
  /**
   * Event of submit.
   */
  const validateAndSubmit = async () => {
    const newIdp = normalizeIdp(currentIdp.value)
    if (!disabledSubmitButton.value && !hasError.value) {
      submitted.value = true
      if (editMode.value) {
        updateIdP(newIdp).then(() => {
          router.push(entity.value.path)
        })
      } else {
        initializeIdP(newIdp).then(() => {
          router.push(entity.value.path)
        })
      }
    }
  }

  /**
   * Event of testing idp config.
   * @returns {Promise} - the notify promise.
   */
  const testIdpConfig = async () => {
    const idpUser = { ...currentIdp.value }
    if (isLdapIdP.value) {
      idpUser.username = currentUser.value.username
      idpUser.password = currentUser.value.password
    }
    if (isSamlIdP.value) {
      delete idpUser.scopes
      delete idpUser.use_ssl
    }
    return validateIdP(idpUser)
  }

  const handleIdPUpdate = (newIdp: IIdp) => {
    currentIdp.value = newIdp
  }
  const handleRolesUpdate = (newRoles: string[]) => {
    currentRoles.value = newRoles
  }
  const handleMappersUpdate = (newMappers: IIdpMapper[]) => {
    currentMappers.value = newMappers
  }
  const handleIdpTypeChange = () => {
    if (mappersCardRef.value) {
      mappersCardRef.value.resetMapper()
    }
  }

  watchEffect(() => {
    if (!currentIdp.value.sign_authn_request && !currentIdp.value.sign_logout_request) {
      currentIdp.value.sp_public_cert = ''
      currentIdp.value.sp_private_cert = ''
    }
  })
</script>

<template>
  <TemplateView
    data-testid="create-idp-view"
    :entity="entity"
    :headerPrimaryAction="submitButton"
    :headerSecondaryAction="cancelButton"
    :headerOptionalAction="isSamlIdP ? testIdpConfigButton : undefined"
    :breadCrumbsProps="breadCrumbs">
    <RouteConfirm :hasPendingChanges="hasPendingChanges"></RouteConfirm>
    <div
      v-if="!loading"
      class="base-cards">
      <BaseCard
        data-testid="add-edit-idp-card"
        :name="idpHeaderLabel">
        <form
          class="create-idp-view"
          @keyup.enter="validateAndSubmit">
          <div class="inputs-row">
            <TextInput
              v-model="currentIdp.idp_name"
              data-testid="idp-name"
              :disabled="editMode"
              :description="t(`${langPath}.template.idp_name.description`)"
              :title="t(`${langPath}.template.idp_name.title`)"
              :errors="idpError.idp_name || undefined"
              required />
            <TextInput
              v-model="currentIdp.idp_label"
              data-testid="idp-label"
              :description="t(`${langPath}.template.idp_label.description`)"
              :title="t(`${langPath}.template.idp_label.title`)"
              required />
            <SelectInput
              v-model="currentIdp.idp_type"
              data-testid="idp-type"
              :disabled="editMode"
              :description="t(`${langPath}.template.idp_type.description`)"
              :title="t(`${langPath}.template.idp_type.title`)"
              :options="idpTypes"
              :default="idpTypes[0]"
              :popper-container-props="{
                positionFixe: true
              }"
              required
              @update:modelValue="handleIdpTypeChange" />
          </div>
        </form>
      </BaseCard>
      <BaseCard
        v-if="isLdapIdP"
        data-testid="ldap-idp-card"
        :name="t(`${langPath}.template.ldapInformations`)">
        <form
          class="create-idp-view"
          @keyup.enter="validateAndSubmit">
          <div class="inputs-row">
            <TextInput
              v-if="isLdapIdP"
              v-model="currentIdp.server"
              data-testid="idp-address"
              :empty="false"
              :description="t(`${langPath}.template.ldap_address.description`)"
              :title="t(`${langPath}.template.ldap_address.title`)"
              required />
            <TextInput
              v-model="currentIdp.domain"
              data-testid="idp-domain"
              :disabled="editMode"
              :empty="false"
              :description="t(`${langPath}.template.domain.description`)"
              :title="t(`${langPath}.template.domain.title`)" />
            <TextInput
              v-model="currentIdp.search"
              data-testid="idp-basedn"
              :empty="false"
              :description="t(`${langPath}.template.baseDn.description`)"
              :title="t(`${langPath}.template.baseDn.title`)"
              required></TextInput>
            <TextInput
              v-model="currentIdp.group"
              data-testid="idp-group"
              :empty="false"
              :description="t(`${langPath}.template.group.description`)"
              :title="t(`${langPath}.template.group.title`)"
              required />
          </div>
          <div class="inputs-row">
            <TextInput
              v-model="currentIdp.bind_dn"
              data-testid="idp-bind-dn"
              :description="t(`${langPath}.template.bindDn.description`)"
              :title="t(`${langPath}.template.bindDn.title`)"
              class="small" />
            <PasswordInput
              v-if="currentIdp?.bind_dn"
              v-model="currentIdp.bind_password"
              data-testid="bind-password"
              :description="t(`${langPath}.template.bindPassword.description`)"
              :title="t(`${langPath}.template.bindPassword.title`)"
              autocomplete="new-password"
              required />
            <TextInput
              v-model="currentIdp.user_filter"
              data-testid="idp-user-filter"
              :description="t(`${langPath}.template.userFilter.description`)"
              :title="t(`${langPath}.template.userFilter.title`)"
              :required="!!currentIdp?.bind_dn" />
            <TextInput
              v-model="currentIdp.search_filter"
              data-testid="idp-search-filter"
              :description="t(`${langPath}.template.searchFilter.description`)"
              :title="t(`${langPath}.template.searchFilter.title`)" />
            <BooleanInput
              v-model="currentIdp.use_ssl"
              data-testid="idp-use-ssl"
              :title="t(`${langPath}.template.useSsl.title`)"
              :description="t(`${langPath}.template.useSsl.description`)" />
          </div>
        </form>
      </BaseCard>
      <BaseCard
        v-if="isSamlIdP"
        data-testid="saml-informations"
        :name="t(`${langPath}.template.samlInformations`)">
        <form
          class="create-idp-view"
          @keyup.enter="validateAndSubmit">
          <div class="inputs-row">
            <TextInput
              v-model="currentIdp.entity_id"
              data-testid="idp-entity-id"
              :empty="false"
              :description="t(`${langPath}.template.entity_id.description`)"
              :title="t(`${langPath}.template.entity_id.title`)"
              required />
            <TextInput
              v-model="currentIdp.single_sign_on_service"
              data-testid="idp-single-sign-on-service"
              :empty="false"
              :description="t(`${langPath}.template.single_sign_on_service.description`)"
              :title="t(`${langPath}.template.single_sign_on_service.title`)"
              required />
            <TextInput
              v-model="currentIdp.single_logout_service"
              data-testid="idp-single-logout-service"
              :empty="false"
              :description="t(`${langPath}.template.single_logout_service.description`)"
              :title="t(`${langPath}.template.single_logout_service.title`)"
              required />
            <TextInput
              v-model="currentIdp.cert_fingerprint"
              data-testid="idp-cert-fingerprint"
              :empty="false"
              :description="t(`${langPath}.template.cert_fingerprint.description`)"
              :title="t(`${langPath}.template.cert_fingerprint.title`)"
              required />
          </div>
          <div class="inputs-row">
            <BooleanInput
              v-model="currentIdp.sign_authn_request"
              data-testid="idp-sign-authn-request"
              :title="t(`${langPath}.template.sign_authn_request.title`)"
              :description="t(`${langPath}.template.sign_authn_request.description`)"></BooleanInput>
            <TextInput
              v-model="currentIdp.sp_public_cert"
              data-testid="idp-sp-public-cert"
              :disabled="!disabledCertificateFields"
              :description="t(`${langPath}.template.sp_public_cert.description`)"
              :title="t(`${langPath}.template.sp_public_cert.title`)"
              :required="disabledCertificateFields" />
          </div>
          <div class="inputs-row">
            <BooleanInput
              v-model="currentIdp.sign_logout_request"
              data-testid="idp-sign-logout-request"
              :title="t(`${langPath}.template.sign_logout_request.title`)"
              :description="t(`${langPath}.template.sign_logout_request.description`)"></BooleanInput>
            <TextInput
              v-model="currentIdp.sp_private_cert"
              data-testid="idp-sp-private-cert"
              :disabled="!disabledCertificateFields"
              :description="t(`${langPath}.template.sp_private_cert.description`)"
              :title="t(`${langPath}.template.sp_private_cert.title`)"
              :required="disabledCertificateFields" />
          </div>
        </form>
      </BaseCard>
      <MappersCard
        ref="mappersCardRef"
        :currentIdp="currentIdp"
        :idpError="idpError"
        :currentMappers="currentMappers"
        :currentRoles="currentRoles"
        @updateCurrentMappers="handleMappersUpdate"
        @updateCurrentRoles="handleRolesUpdate"
        @updateCurrentIdp="handleIdPUpdate" />
      <SeparatorHeader
        v-if="isLdapIdP"
        data-testid="test-ldap-config"
        :collapseValue="false"
        :icon="EIconSettings.Settings2"
        :name="t(`${langPath}.template.testConfig`)">
        <BaseCard
          data-testid="test-idp-config-card"
          :name="`Test ${currentIdp?.idp_type?.toUpperCase()} config`"
          :headerPrimaryAction="testIdpConfigButton">
          <form
            class="create-idp-view"
            @keyup.enter="testIdpConfig">
            <div class="inputs-row">
              <TextInput
                v-if="isLdapIdP"
                v-model="currentUser.username"
                data-testid="current-username"
                title="Username"
                autocomplete="username"
                required></TextInput>
              <PasswordInput
                v-if="isLdapIdP"
                v-model="currentUser.password"
                data-testid="current-password"
                title="Password"
                required
                autocomplete="new-password" />
            </div>
          </form>
        </BaseCard>
      </SeparatorHeader>
      <SeparatorHeader
        v-if="isSamlIdP && editMode"
        data-testid="test-saml-config"
        :collapseValue="false"
        :icon="EIconSettings.Settings2"
        :name="t(`users.idp.spMetadata.spMetadata`)"
        :secondaryAction="refreshMetadataButton">
        <BaseCard
          data-testid="saml-sp-metadata"
          :name="t(`users.idp.spMetadata.spMetadata`)"
          :headerPrimaryAction="downloadSpMetadataButton"
          :headerSecondaryAction="copyToClipboardButton">
          <template v-if="spMetadata">
            <div
              v-if="redirectUri"
              class="group-icon">
              <TextInput
                data-testid="view-sp-metadata-redirect-uri"
                :title="t(`users.idp.spMetadata.redirectUri.title`)"
                :description="t(`users.idp.spMetadata.redirectUri.description`)"
                :modelValue="redirectUri"
                locked />
            </div>
            <DownloadAnchor
              :fileName="`${props.idpName?.replace(/[^a-zA-Z0-9_-]+/g, '_')}_sp_metadata`"
              :typeFile="EFileType.XML_FILE_TYPE"
              :content="downloadContent" />
          </template>
          <template v-else>
            <BubbleText
              data-testid="sp-metadata-error"
              :label="t('users.idp.spMetadata.error')" />
          </template>
        </BaseCard>
      </SeparatorHeader>
    </div>
  </TemplateView>
</template>

<style scoped lang="scss">
  .create-idp-view {
    display: flex;
    flex-direction: column;

    .inputs-row {
      display: flex;
      gap: 16px;
      width: 100%;

      > * {
        flex: 1 1 0;
        min-width: 0;
        box-sizing: border-box;
      }
    }

    .inputs-bottom {
      display: flex;
      flex-direction: column;
      gap: 16px;
      width: 100%;

      > * {
        width: 100%;
        min-width: 0;
        box-sizing: border-box;
      }
    }
  }
  .idp-type-select-input {
    position: relative;
    top: -64px;
    left: 128px;
  }
  .base-cards {
    display: flex;
    flex-direction: column;
    gap: 16px; /* Adjust padding as needed */
  }
</style>
