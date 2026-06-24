<script setup lang="ts">
  import BaseCard from '@ateme/cathodic-ui/src/components/containers/BaseCard.vue'
  import { IIdp, IIdpMapper, IRole, IUnknownObjectKeys } from '@interfaces/Interfaces.ts'
  import BaseTable from '@ateme/cathodic-ui/src/components/collections/BaseTable.vue'
  import ChipInput from '@ateme/cathodic-ui/src/components/inputs/ChipInput.vue'
  import BooleanInput from '@ateme/cathodic-ui/src/components/inputs/BooleanInput.vue'
  import SelectInput from '@ateme/cathodic-ui/src/components/inputs/SelectInput.vue'
  import { IColumn } from '@ateme/cathodic-ui/src/interfaces/Table.d'
  import { computed, onMounted, ref } from 'vue'
  import { useTranslation } from 'i18next-vue'
  import SeparatorHeader from '@ateme/cathodic-ui/src/components/elements/SeparatorHeader.vue'
  import ModalOverlay from '@ateme/cathodic-ui/src/components/containers/ModalOverlay.vue'
  import OverlayCard from '@ateme/cathodic-ui/src/components/containers/OverlayCard.vue'
  import type { BaseButtonDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons.d.ts'
  import { EIconEdit, EIconSettings, EIconValidations } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
  import TextInput from '@ateme/cathodic-ui/src/components/inputs/TextInput.vue'
  import { useIdpManagement } from '../../../components/idp/composables/idpComposable.ts'
  import { rolesStore } from '../../../components/roles/store'
  import { storeToRefs } from 'pinia'
  import { EDataType } from '@ateme/cathodic-ui/src/interfaces/TableEnum.ts'
  import BubbleText from '@ateme/cathodic-ui/src/components/elements/BubbleText.vue'
  import { EBubbleTextType } from '@ateme/cathodic-ui/src/interfaces/BubbleTextEnum'
  import type { BaseTagDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/tags.d.ts'
  import { ISelectInputOption } from '@ateme/cathodic-ui/src/interfaces/SelectInput.ts'
  import { ConfirmButtonsDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons'
  // #####################################
  // INJECT
  // #####################################
  // -------------------
  // i18n
  // -------------------
  const { t } = useTranslation()
  // -------------------
  // store
  // -------------------
  const storeRoles = rolesStore()
  const { getAllRoles } = storeToRefs(storeRoles)

  const langPath: string = 'users.idp.roleMapping.mapper'

  // -------------------
  // composable
  // -------------------
  const { getRoleLabel } = useIdpManagement()

  // #####################################
  // PROPS / EVENTS
  // #####################################
  export type MappersCardProps = {
    /**
     * Selected idp for edit.
     */
    currentMappers?: IIdpMapper[]
    currentIdp: IIdp
    currentRoles?: string[]
    idpError: IUnknownObjectKeys
  }

  const props = withDefaults(defineProps<MappersCardProps>(), {
    currentMappers: () => [],
    currentRoles: () => []
  })

  const emit = defineEmits<{
    (e: 'updateCurrentMappers', value: IIdpMapper[]): void
    (e: 'updateCurrentRoles', value: string[]): void
    (e: 'updateCurrentIdp', value: IIdp): void
  }>()

  const mappersColumns = ref<IColumn[]>([
    {
      name: t(`${langPath}.type.title`),
      path: 'type',
      resizable: true,
      sortable: true
    },
    {
      name: t(`${langPath}.attributeName`),
      path: 'attribute_name',
      resizable: true,
      sortable: true
    },
    {
      name: t(`${langPath}.attributeValue`),
      path: 'attribute_value',
      resizable: true,
      sortable: true
    },
    {
      name: t(`${langPath}.rolesToAdd`),
      path: 'roles_to_add',
      dataType: EDataType.Tag,
      resizable: true
    }
  ])

  const showAddMapper = ref<boolean>(false)
  const idpMapperModel = ref<IIdpMapper>({})
  const idpMapperTypes = ref<ISelectInputOption[]>([
    { label: t(`${langPath}.type.direct`), value: 'direct' },
    { label: t(`${langPath}.type.simple`), value: 'simple' }
  ])
  const selectedMapper = ref<IIdpMapper | undefined>(undefined)
  const idpMapperError = ref<IUnknownObjectKeys>({})
  const defaultMapper = ref<IIdpMapper>({})
  const isEditMapper = ref<boolean>(false)

  // #####################################
  // HOOK
  // #####################################

  onMounted(() => {
    initData()
    initMapper()
  })
  // #####################################
  // COMPUTED
  // #####################################
  /**
   * Current mapper
   * @returns {IIdpMapper | undefined} - The current mapper
   */
  const mapperCurrent = computed(
    (): IIdpMapper | undefined =>
      props.currentIdp?.mappers?.find((item: IIdpMapper) => item._id === selectedMapper.value) ?? undefined
  )
  /**
   * Test if there a change.
   * @returns {boolean} - <true> has change, <false> has no change
   */
  const hasChange = computed((): boolean => {
    if (!mapperCurrent.value) {
      return JSON.stringify(defaultMapper.value) !== JSON.stringify(idpMapperModel.value)
    }
    return JSON.stringify(mapperCurrent.value) !== JSON.stringify(idpMapperModel.value)
  })
  /**
   * Getter for the confirmButton of the modal - Return the cancel and the submit buttons
   * @returns {ConfirmButtonsDef} - The confirm buttons for the modal
   */
  const confirmButtons = computed((): ConfirmButtonsDef => {
    return {
      onCancel: exitModal,
      onConfirm: () => validateAndSubmit(),
      confirmLabel: t('users.main.submit'),
      disabledConfirm: hasError.value || !hasChange.value
    }
  })

  /**
   * primary action for mappers
   * @returns {BaseButtonDef} - The primary action for mappers
   */
  const mappersPrimaryAction = computed((): BaseButtonDef => {
    return {
      label: t('common.add'),
      title: t('common.addTitleM', { name: t(`${langPath}.title`).toLowerCase() }),
      icon: EIconValidations.AddCircle,
      id: 'show-add-new-mapper-button',
      eventClick: () => (showAddMapper.value = !showAddMapper.value)
    } as BaseButtonDef
  })
  /**
   * Is the type 'simple' selected.
   * @returns {boolean} - True if the simple type is selected
   */
  const isTypeSimpleSelected = computed((): boolean => {
    return idpMapperModel.value.type === 'simple'
  })
  /**
   * Is the type 'direct' selected.
   * @returns {boolean} - True if the direct type is selected
   */
  const isTypeDirectSelected = computed((): boolean => {
    return idpMapperModel.value.type === 'direct'
  })
  /**
   * Test if there is a error.
   * @returns {boolean} - True if there is an error
   */
  const hasError = computed((): boolean => {
    if (idpMapperModel.value) {
      return updateErrorInput()
    }
    return false
  })
  /**
   * Is the idp type 'ldap'
   * @returns {boolean} - True if the idp is an ldap one
   */
  const isLdapIdP = computed((): boolean => {
    return props.currentIdp.idp_type === 'ldap'
  })
  /**
   * Is the idp type 'saml'
   * @returns {boolean} - True if the idp is an saml one
   */
  const isSamlIdP = computed((): boolean => {
    return props.currentIdp.idp_type === 'saml'
  })
  /**
   * Show user filter warning
   * @returns {boolean} - show the message or not
   */
  const showUserFilterWarning = computed((): boolean => {
    return isLdapIdP.value && props.currentMappers?.length > 0 && !props.currentIdp?.user_filter
  })

  /**
   * reactive current IdP
   * @returns {IIdp} - The current IdP
   */
  const currentIdpModel = computed({
    get: () => props.currentIdp,
    set: (value: IIdp) => {
      emit('updateCurrentIdp', value)
    }
  })

  /**
   * Filtered mappers to show
   * @returns {IIdpMapper[]} - The filtered mappers to show
   */
  const displayedMappers = computed((): IIdpMapper[] => {
    return props.currentMappers.map((mapper: IIdpMapper) => ({
      ...mapper,
      roles_to_add: formatRoles(mapper)
    })) as IIdpMapper[]
  })
  // #####################################
  // METHODS
  // #####################################
  /**
   * Init default data for the mapper.
   */
  const initData = () => {
    defaultMapper.value = isSamlIdP.value
      ? {
          type: 'direct',
          attribute_name: '',
          attribute_value: '',
          roles_to_add: []
        }
      : {
          type: 'simple',
          attribute_name: 'memberof',
          attribute_value: '',
          roles_to_add: []
        }
  }
  /**
   * Init the mapper.
   */
  const initMapper = () => {
    if (!mapperCurrent.value) {
      idpMapperModel.value = { ...defaultMapper.value }
    } else {
      idpMapperModel.value = { ...mapperCurrent.value }
    }
  }
  /**
   * Reset the mapper.
   */
  const resetMapper = () => {
    initData()
    idpMapperModel.value = { ...defaultMapper.value }
    selectedMapper.value = undefined
    isEditMapper.value = false
  }
  /**
   * Expose the resetMapper function So that it can reset mapper data when changing idp type on the parent component
   */
  defineExpose({
    resetMapper
  })

  /**
   * Format roles for the current mapper.
   * @param {IIdpMapper} mapper - The mapper to get roles from
   * @returns {BaseTagDef[]} - The formatted roles
   */
  const formatRoles = (mapper: IIdpMapper): BaseTagDef[] => {
    return mapper.roles_to_add?.reduce((acc: BaseTagDef[], id: string): BaseTagDef[] => {
      if (id !== 'usr:guest') {
        const role: IRole | undefined = getAllRoles.value.find((role: IRole) => role.id === id)
        acc.push(
          role?.title ? { label: role.title as string } : { label: t(`${langPath}.noFoundRole`, { id }) as string }
        )
      }
      return acc
    }, []) as BaseTagDef[]
  }
  /**
   * Update the error input.
   * @returns {boolean} - True if there is an error
   */
  const updateErrorInput = (): boolean => {
    if (!idpMapperModel.value) return true

    idpMapperError.value = {}

    // Validation de attribute_name
    const nameRegex = /^[A-Za-z][A-Za-z0-9/:_\\.]*$/
    if (!idpMapperModel.value.attribute_name) {
      idpMapperError.value.attribute_name = t('users.errors.fieldMandatory')
    } else if (!nameRegex.test(idpMapperModel.value.attribute_name)) {
      idpMapperError.value.attribute_name = t('users.errors.invalidFormat')
    }

    // Validation supplémentaire
    if (isTypeSimpleSelected.value) {
      validateSimpleTypeFields()
    }

    validateDuplicateMapper()

    return Object.keys(idpMapperError.value).length > 0
  }

  /**
   * Validate the simple type fields
   */
  const validateSimpleTypeFields = () => {
    if (!idpMapperModel.value) return

    if (!idpMapperModel.value.attribute_value) {
      idpMapperError.value.attribute_value = t('users.errors.fieldMandatory')
    }

    if (!idpMapperModel.value.roles_to_add?.length) {
      idpMapperError.value.roles_to_add = [t(`${langPath}.oneRoleMandatory`)]
    }
  }

  /**
   * Check if a mapper already exists with the same attribute_name and attribute_value.
   */
  const validateDuplicateMapper = () => {
    if (!isEditMapper.value && idpMapperModel.value) {
      const alreadyExist = props.currentMappers.some(
        (item: IIdpMapper) =>
          item.attribute_name === idpMapperModel.value!.attribute_name &&
          item.attribute_value === idpMapperModel.value!.attribute_value
      )
      if (alreadyExist) {
        idpMapperError.value.attribute_name = t('users.errors.alreadyExistMapper')
      }
    }
  }

  /**
   * Event of submit.
   */
  const validateAndSubmit = async () => {
    if (!hasError.value) {
      showAddMapper.value = false
      const newMappers = [...props.currentMappers]
      if (isEditMapper.value) {
        newMappers.splice(
          newMappers.findIndex((item: IIdpMapper) => item._id === mapperCurrent.value?._id),
          1,
          idpMapperModel.value as IIdpMapper
        )
      } else {
        newMappers.push(idpMapperModel.value as IIdpMapper)
      }
      emit('updateCurrentMappers', newMappers)
      resetMapper()
    }
  }

  /**
   * Returns the buttons to display.
   * @param {IIdpMapper} mapper -  The mapper concerned by the buttons
   * @returns {BaseButtonDef[]} - The buttons to return
   */
  const mappersTableActionButtons = (mapper: IIdpMapper): BaseButtonDef[] => {
    return [
      {
        icon: EIconEdit.Edit,
        title: t('users.table.actions.edit', { name: mapper.attribute_name }),
        id: `update-mapper-${mapper.attribute_name}`,
        eventClick: () => editMapper(mapper)
      } as BaseButtonDef,
      {
        icon: EIconEdit.Delete,
        title: t('users.table.actions.delete', { name: mapper.attribute_name }),
        id: `delete-mapper-${mapper.attribute_name}`,
        eventClick: () => deleteMapper(mapper)
      } as BaseButtonDef
    ]
  }

  /**
   * Handle the change of deny_access value and emit an event to update the IDP
   * @param {boolean} value - New value of deny_access
   */
  const handleDenyAccessChange = (value: boolean) => {
    if (props.currentIdp) {
      const updatedIdp = { ...props.currentIdp, deny_access: value }
      emit('updateCurrentIdp', updatedIdp)
    }
  }

  /**
   * Send edition of the mapper
   * @param {IIdpMapper} mapper - The mapper to edit
   */
  const editMapper = (mapper: IIdpMapper) => {
    isEditMapper.value = true
    idpMapperModel.value = {
      ...props.currentMappers.find((item: IIdpMapper) => item.attribute_value === mapper.attribute_value)
    }
    showAddMapper.value = true
  }

  /**
   * Delete the mapper from the list
   * @param {IIdpMapper} mapper - Mapper to delete
   */
  const deleteMapper = (mapper: IIdpMapper) => {
    const newMappers = [...props.currentMappers]
    // Recherche par ID d'abord, puis par attribut_name et attribut_value en fallback
    const index = newMappers.findIndex(
      (item: IIdpMapper) =>
        (mapper._id && item._id === mapper._id) ||
        (item.attribute_name === mapper.attribute_name && item.attribute_value === mapper.attribute_value)
    )

    if (index !== -1) {
      newMappers.splice(index, 1)
      emit('updateCurrentMappers', newMappers)
    }
  }
  /**
   * Handles update of roles with type validation
   * @param {(string | number)[] | undefined} value - New roles
   */
  const handleRolesUpdate = (value: (string | number)[] | undefined) => {
    if (value) {
      // Conversion et validation des valeurs
      const stringRoles = value
        .filter((v): v is string => typeof v === 'string')
        .concat(value.filter((v): v is number => typeof v === 'number').map(v => v.toString()))

      if (stringRoles.length > 0) {
        emit('updateCurrentRoles', stringRoles)
      }
    } else {
      // Si undefined, émettre un tableau vide
      emit('updateCurrentRoles', [])
    }
  }
  /**
   * Exit the modal and reset the mapper.
   */
  const exitModal = () => {
    showAddMapper.value = false
    resetMapper()
  }
</script>

<template>
  <ModalOverlay v-if="showAddMapper">
    <OverlayCard
      data-testid="add-mappers-overlay-card"
      :name="isEditMapper ? t(`${langPath}.edit`) : t(`${langPath}.add`)"
      :onLastAction="exitModal"
      :onExit="exitModal"
      :confirmButtons="confirmButtons"
      class="add-mappers-card">
      <div v-if="idpMapperModel">
        <form
          class="add-update-idp-mapper-form"
          @keyup.enter="validateAndSubmit">
          <SelectInput
            v-if="isSamlIdP"
            v-model="idpMapperModel.type"
            data-testid="idp-mapper-type"
            :title="t(`${langPath}.type.title`)"
            :options="idpMapperTypes"
            required />
          <TextInput
            v-model="idpMapperModel.attribute_name"
            data-testid="idp-mapper-attribute-name"
            :title="t(`${langPath}.attributeName`)"
            :description="t(`${langPath}.attributeNameFormat`)"
            :error="idpMapperError.attribute_name"
            required />
          <template v-if="isTypeSimpleSelected">
            <TextInput
              v-model="idpMapperModel.attribute_value"
              data-testid="idp-mapper-attribute-value"
              :title="t(`${langPath}.attributeValue`)"
              :disabled="isTypeDirectSelected || isEditMapper"
              :error="idpMapperError.attribute_value"
              required />
            <ChipInput
              v-model="idpMapperModel.roles_to_add"
              data-testid="idp-mapper-roles-to-add"
              :title="t(`${langPath}.rolesToAdd`)"
              :disabled="isTypeDirectSelected"
              :options="
                getAllRoles.map(role => ({
                  label: role.title as string,
                  value: role.id as string
                }))
              "
              :content="getRoleLabel"
              :errors="idpMapperError.roles_to_add"
              :popper-container-props="{
                positionFixe: true
              }"
              autocomplete="off"
              strict
              required />
          </template>
        </form>
      </div>
    </OverlayCard>
  </ModalOverlay>
  <SeparatorHeader
    data-testid="role-mapping-default-behavior"
    :name="t(`users.idp.roleMapping.default.title`)"
    :icon="EIconSettings.Settings2">
    <BaseCard
      data-testid="roles-base-card"
      name="Roles">
      <form class="create-idp-view">
        <div class="inputs-row">
          <BooleanInput
            v-if="currentIdp"
            v-model="currentIdpModel.deny_access"
            data-testid="idp-default-behavior-deny-access"
            class="default-behavior-select-input"
            :description="t(`users.idp.roleMapping.default.question`)"
            :title="t(`users.idp.roleMapping.default.denyAccess`)"
            @update:modelValue="value => handleDenyAccessChange(value)"></BooleanInput>
          <ChipInput
            v-if="!currentIdp.deny_access"
            v-model="currentIdpModel.roles"
            data-testid="idp-default-behavior-roles"
            :options="
              getAllRoles.map(role => ({
                label: role.title as string,
                value: role.id as string
              }))
            "
            :content="getRoleLabel"
            :errors="idpError.roles"
            :title="t(`users.idp.roleMapping.default.rolesToAdd`)"
            class="default-behavior-roles-input"
            :popper-container-props="{
              positionFixe: true
            }"
            strict
            required
            @update:modelValue="handleRolesUpdate" />
        </div>
      </form>
    </BaseCard>
  </SeparatorHeader>
  <SeparatorHeader
    data-testid="role-mapping-mappers"
    :name="t(`users.idp.roleMapping.mappers`)"
    :icon="EIconSettings.Settings2">
    <BubbleText
      v-if="showUserFilterWarning"
      data-testid="user-filter-warning-message"
      :type="EBubbleTextType.Warning"
      :label="t(`users.idp.roleMapping.mapper.mappersWarning`)"
      class="user-filter-warning-message" />
    <BaseCard
      data-testid="mappers-base-card"
      :name="t(`users.idp.roleMapping.mappers`)"
      :headerPrimaryAction="mappersPrimaryAction">
      <BaseTable
        data-testid="mappers-base-table"
        :columnList="mappersColumns"
        :data="displayedMappers"
        localStorageKey="IDP_MAPPERS_TABLE"
        :actionColumn="mappersTableActionButtons"
        hasPageFeature />
    </BaseCard>
  </SeparatorHeader>
</template>

<style lang="scss" scoped>
  .create-idp-view {
    display: flex;
    flex-direction: column;

    .inputs-row {
      display: flex;
      gap: 16px;

      .default-behavior-select-input {
        width: 20% !important;
      }
      .default-behavior-roles-input {
        width: 80% !important;
      }
    }
  }
  .user-filter-warning-message {
    margin-bottom: var(--spacing-base);
  }
  .add-mappers-card {
    width: 500px;
  }
</style>
