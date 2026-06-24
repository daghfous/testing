<script lang="ts" setup>
  import { EIconEdit, EIconValidations } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
  import BaseCard from '@ateme/cathodic-ui/src/components/containers/BaseCard.vue'
  import type { BaseButtonDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons.d.ts'
  import ConfirmationLayout from '@ateme/cathodic-ui/src/components/layouts/ConfirmationLayout.vue'
  import ModalOverlay from '@ateme/cathodic-ui/src/components/containers/ModalOverlay.vue'
  import OverlayCard from '@ateme/cathodic-ui/src/components/containers/OverlayCard.vue'
  import { storeToRefs } from 'pinia'
  import { computed, onBeforeMount, ref } from 'vue'
  import { useTranslation } from 'i18next-vue'
  import { IColumn } from '@ateme/cathodic-ui/src/interfaces/Table.d'
  import BaseTable from '@ateme/cathodic-ui/src/components/collections/BaseTable.vue'
  import { EButtonType } from '@ateme/cathodic-ui/src/interfaces/ButtonEnum'
  import { IRole } from '@interfaces/Interfaces'
  import { rolesStore } from '@store/allStoreDefinition.ts'
  import { useRoleManagement } from '../../components/roles/composables/rolesComposable.ts'
  import { ConfirmButtonsDef, DropdownButtonDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons'
  import { upperFirst } from '@ateme/cathodic-ui/src/utils/StringUtils.ts'

  // -------------------
  // i18n
  // -------------------
  const { t } = useTranslation()
  // -------------------
  // store
  // -------------------
  const storeRoles = rolesStore()
  const { fillRoles } = storeRoles
  const { getAllRoles } = storeToRefs(storeRoles)
  // -------------------
  // INJECT
  // -------------------
  const langPath: string = 'users.roles'
  // -------------------
  // composable
  // -------------------
  const { clickExpertMode, expertMode, expertModeLabel, expertModeIcon } = useRoleManagement()

  // #####################################
  // PROPS / EVENTS
  // #####################################
  export type RolesBaseCardProps = {
    currentRolesIds: string[]
    defaultBehavior?: boolean
  }

  const props = withDefaults(defineProps<RolesBaseCardProps>(), {
    roleToDuplicate: undefined,
    roleToEdit: undefined,
    currentRolesIds: () => [],
    defaultBehavior: false
  })

  const emit = defineEmits<{
    (e: 'update:currentRoles', value: IRole[]): void
  }>()

  onBeforeMount(async () => {
    await fillRoles()
  })
  // #####################################
  // DATA
  // #####################################
  const showAddRole = ref<boolean>(false)
  const showDeleteRole = ref<boolean>(false)
  const roleToDelete = ref<string | undefined>(undefined)
  const selectedRolesToSend = ref<IRole[]>([])
  const selectedRolesToDelete = ref<IRole[]>([])
  const selectedRolesNumber = ref<number>(0)
  const selectedRolesToDeleteNumber = ref<number>(0)
  const denyAccess = ref<boolean>(false)
  const rolesColumns = ref<IColumn[]>([
    {
      name: t(`${langPath}.view.title`),
      path: 'title',
      sortable: true,
      resizable: true
    },
    {
      name: t(`${langPath}.view.label`),
      path: 'label',
      sortable: true,
      resizable: true
    },
    {
      name: t(`${langPath}.view.description`),
      path: 'description',
      sortable: true,
      resizable: true
    }
  ])

  // #####################################
  // COMPUTED
  // #####################################
  const addRolePrimaryAction = computed((): BaseButtonDef => {
    return {
      label: expertModeLabel.value,
      icon: expertModeIcon.value,
      type: expertMode.value ? EButtonType.Primary : EButtonType.Secondary,
      eventClick: () => {
        clickExpertMode()
        fillRoles()
      }
    }
  })

  /**
   * Get the available list of roles filtered to exclude the roles passed in props.
   * @returns {IRole[]} - The available list of roles filtered to exclude the roles passed in props.
   */
  const availableRolesList = computed((): IRole[] => {
    return getAllRoles.value.filter(role => !props.currentRolesIds.includes(role.id as string))
  })

  /**
   * Get the current list of roles based on the list of role identifiers passed in props.
   * @returns {IRole[]} The list of current roles.
   */
  const currentRoles = computed((): IRole[] => {
    return getAllRoles.value.filter(role => props.currentRolesIds.includes(role.id as string))
  })

  /**
   * Get a list of roles to display, with each role
   * augmented to include a `role_unicity_key` property. The `role_unicity_key` is
   * a unique identifier for each role, created by concatenating the `title` and
   * `label` properties of the role using a comma separator.
   *
   * This property computes its value based on the `availableRolesList` observable.
   * If `availableRolesList` has no value, an empty array is returned.
   * @returns {IRole[]} A list of role objects including `role_unicity_key` for each role.
   */
  const displayedRolesToAdd = computed((): IRole[] => {
    return (
      availableRolesList?.value.map((role: IRole) => {
        const displayedRole = { ...role }
        displayedRole.role_unicity_key = `${displayedRole.title},${displayedRole.label}`
        return displayedRole
      }) || []
    )
  })

  /**
   * Get list of current roles with an additional property `role_unicity_key`.
   *
   * This variable transforms the `currentRoles` prop, adding a uniquely identifiable key
   * to each role object. The `role_unicity_key` is created by concatenating the `title`
   * and `label` properties of the role, separated by a comma.
   * @constant {IRole[]} displayedCurrentRoles - The transformed list of roles with an added `role_unicity_key`.
   */
  const displayedCurrentRoles = computed((): IRole[] => {
    return currentRoles.value.map((role: IRole) => {
      const displayedRole = { ...role }
      displayedRole.role_unicity_key = `${displayedRole.title},${displayedRole.label}`
      return displayedRole
    })
  })
  /**
   * The primary button of the roles base card. Used to open the add roles modal
   * @returns {BaseButtonDef} The button.
   */
  const rolesPrimaryAction = computed((): BaseButtonDef => {
    return {
      label: t('common.add'),
      title: t('common.addTitleM', { name: 'role' }),
      icon: EIconValidations.AddCircle,
      eventClick: () => addRoles()
    } as BaseButtonDef
  })
  /**
   * Getter for the confirmButton of the modal - Return the cancel and the add buttons
   * @returns {ConfirmButtonsDef} - The confirm buttons for the modal
   */
  const confirmButtons = computed((): ConfirmButtonsDef => {
    return {
      onCancel: exitModal,
      onConfirm: () => submitNewRoles(selectedRolesToSend.value),
      confirmIcon: EIconValidations.AddCircle,
      confirmLabel: t('common.add'),
      disabledConfirm: selectedRolesNumber.value === 0
    }
  })
  /**
   * Header button for all bulk actions button (delete, ...)
   * @returns {DropdownButtonDef} - The dropdown button definition for bulk actions
   */
  const bulkActionsButton = computed((): DropdownButtonDef => {
    return {
      label: upperFirst(t('common.actions')),
      title: t('common.actions'),
      icon: EIconValidations.CheckBox,
      disabled: selectedRolesToDeleteNumber.value === 0,
      itemList: [
        {
          icon: EIconEdit.Delete,
          name: t('common.delete'),
          disabled: selectedRolesToDeleteNumber.value === 0,
          title: t('common.deleteSelectedTitleM', { name: 'roles' }),
          eventClick: () => deleteSelectedRoles()
        }
      ]
    }
  })
  // #####################################
  // METHODS
  // #####################################
  /**
   * Method to open the add roles modal
   */
  const addRoles = () => {
    showAddRole.value = true
  }
  /**
   * List of roles to add to the roles base card list.
   * @param {string[]} rows - The list of roles identifiers to add to the roles base card list.
   */
  const selectRolesToAdd = (rows: string[]) => {
    selectedRolesToSend.value = rows.map((roleUnicityKey: string) => {
      const role = getAllRoles.value.find((role: IRole) => `${role.title},${role.label}` === roleUnicityKey)
      return role as IRole
    })

    selectedRolesNumber.value = rows.length
  }

  /**
   * List of roles to delete from the roles base card list.
   * @param {string[]} rows - The list of roles identifiers to delete from the roles base card list.
   */
  const selectRolesToDelete = (rows: string[]) => {
    selectedRolesToDelete.value = rows.map((roleUnicityKey: string) => {
      const role = getAllRoles.value.find((role: IRole) => `${role.title},${role.label}` === roleUnicityKey)
      return role as IRole
    })

    selectedRolesToDeleteNumber.value = rows.length
  }

  /**
   * Delete selected roles from the roles base card list.
   * The method emits an event to update the `currentRoles` prop by filtering out the roles that are selected for deletion.
   * It uses the `id` property of the roles to identify which roles to remove from the list.
   * After updating the list of current roles, it resets the selected roles to delete and their count.
   */
  const deleteSelectedRoles = () => {
    emit(
      'update:currentRoles',
      currentRoles.value.filter((role: IRole) => {
        const userRoles = selectedRolesToDelete.value.map(r => r.id)
        return !userRoles.includes(role.id as string)
      })
    )
    selectRolesToDelete([])
  }

  /**
   * Add roles to the roles base card list.
   * @param {IRole[]} newRoles - The list of roles to add to the roles base card list.
   */
  const submitNewRoles = (newRoles: IRole[]) => {
    const rolesToSend = [...currentRoles.value]
    newRoles.map(newRoleToSend => {
      rolesToSend.push(newRoleToSend)
    })
    emit('update:currentRoles', rolesToSend)
    exitModal()
  }

  /**
   * Update route for deletion with a role id
   * @param {string} id - The role's id to delete
   */
  const deleteRole = async (id: string) => {
    roleToDelete.value = id

    onDeleteRole()
  }

  /**
   * Delete a role from the roles base card list.
   * The method emits an event to update the `currentRoles` prop by filtering out the role that is selected for deletion.
   */
  const onDeleteRole = () => {
    emit(
      'update:currentRoles',
      currentRoles.value.filter((role: IRole) => role.id !== roleToDelete.value)
    )
    roleToDelete.value = undefined
    showDeleteRole.value = false
  }

  /**
   * Button on the roles base card table to delete a role.
   * @param {IRole} line - the line to delete role from
   * @returns {BaseButtonDef[]} - The button to delete a role.
   */
  const rolesActionButton = (line: IRole): BaseButtonDef[] => {
    return [
      {
        icon: EIconEdit.Delete,
        label: t('common.delete'),
        title: t('users.table.actions.delete', { name: line.title }),
        eventClick: () => deleteRole(line.id as string)
      }
    ] as BaseButtonDef[]
  }

  /**
   * Closes the modal and reset the selected roles
   */
  const exitModal = () => {
    showAddRole.value = false
    selectedRolesNumber.value = 0
    selectedRolesToSend.value = []
  }
</script>

<template>
  <div>
    <ModalOverlay v-if="showAddRole">
      <OverlayCard
        data-testid="add-roles-overlay-card"
        :name="t(`${langPath}.addRoles`)"
        :hasChange="() => selectedRolesNumber > 0"
        :onLastAction="exitModal"
        :onExit="exitModal"
        :headerPrimaryAction="addRolePrimaryAction"
        :confirmButtons="confirmButtons"
        class="add-roles-card">
        <BaseTable
          data-testid="add-roles-base-table"
          class="add-roles-table"
          :columnList="rolesColumns"
          :data="displayedRolesToAdd"
          hasPageFeature
          lineIdentifier="role_unicity_key"
          localStorageKey="ROLES_BASE_CARD_ADD_ROLES_TABLE"
          @select="selectRolesToAdd" />
      </OverlayCard>
    </ModalOverlay>
    <ModalOverlay v-if="showDeleteRole">
      <ConfirmationLayout
        data-testid="delete-roles-confirmation-layout"
        :onConfirm="onDeleteRole"
        :onCancel="() => (showDeleteRole = false)"
        :primaryMessage="
          t(`users.confirmationMessageBeginning`) + ' ' + t(`users.deleteRole.confirmationMessageRole`)
        " />
    </ModalOverlay>
    <BaseCard
      data-testid="current-roles-base-card"
      :name="t('users.main.roles')"
      :headerPrimaryAction="rolesPrimaryAction"
      :headerSecondaryAction="bulkActionsButton">
      <BaseTable
        v-if="!defaultBehavior || (defaultBehavior && !denyAccess)"
        data-testid="current-roles-base-table"
        :columnList="rolesColumns"
        :data="displayedCurrentRoles"
        hasPageFeature
        lineIdentifier="role_unicity_key"
        localStorageKey="ROLES_BASE_CARD_ROLES_TABLE"
        :actionColumn="rolesActionButton"
        @select="selectRolesToDelete" />
    </BaseCard>
  </div>
</template>

<style lang="scss" scoped>
  .add-roles-card {
    overflow: auto;
    max-width: calc(100vw - 20px);
    .add-roles-table {
      max-width: 70vw;
      max-height: 70vh;
    }
  }
</style>
