<script lang="ts" setup>
  import { EIconEdit, EIconValidations } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
  import BaseCard from '@ateme/cathodic-ui/src/components/containers/BaseCard.vue'
  import type { BaseButtonDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons.d.ts'
  import ConfirmationLayout from '@ateme/cathodic-ui/src/components/layouts/ConfirmationLayout.vue'
  import ModalOverlay from '@ateme/cathodic-ui/src/components/containers/ModalOverlay.vue'
  import OverlayCard from '@ateme/cathodic-ui/src/components/containers/OverlayCard.vue'
  import { storeToRefs } from 'pinia'
  import { computed, ref } from 'vue'
  import { useTranslation } from 'i18next-vue'
  import { IColumn } from '@ateme/cathodic-ui/src/interfaces/Table.d'
  import BaseTable from '@ateme/cathodic-ui/src/components/collections/BaseTable.vue'
  import { IRoleAction } from '@interfaces/Interfaces'
  import { rolesStore } from '@store/allStoreDefinition.ts'
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
  const { getActions } = storeToRefs(storeRoles)
  // -------------------
  // INJECT
  // -------------------
  const langPath: string = 'users.roles'

  // #####################################
  // PROPS / EVENTS
  // #####################################
  export type ActionsBaseCardProps = {
    /**
     * Selected idp for edit.
     */
    availableActionsList?: IRoleAction[]
    editMode?: boolean
    currentActions: IRoleAction[]
  }
  const props = withDefaults(defineProps<ActionsBaseCardProps>(), {
    actionToDuplicate: undefined,
    actionToEdit: undefined,
    currentActions: () => []
  })

  const emit = defineEmits<{
    (e: 'update:currentActions', value: IRoleAction[]): void
  }>()
  // #####################################
  // DATA
  // #####################################
  const showAddAction = ref<boolean>(false)
  const showDeleteAction = ref<boolean>(false)
  const actionToDelete = ref<string | undefined>(undefined)
  const selectedActionsToSend = ref<IRoleAction[]>([])
  const selectedActionsToDelete = ref<IRoleAction[]>([])
  const selectedActionsNumber = ref<number>(0)
  const selectedActionsToDeleteNumber = ref<number>(0)
  const actionsColumns = ref<IColumn[]>([
    {
      name: t(`${langPath}.addActions.columns.action`),
      path: 'title',
      sortable: true,
      resizable: true
    },
    {
      name: t(`${langPath}.addActions.columns.label`),
      path: 'label',
      sortable: true,
      resizable: true
    },
    {
      name: t(`${langPath}.addActions.columns.description`),
      path: 'description',
      sortable: true,
      resizable: true
    }
  ])

  // #####################################
  // COMPUTED
  // #####################################
  const actionsPrimaryAction = computed((): BaseButtonDef => {
    return {
      label: t('common.add'),
      title: t('common.addTitleF', { name: 'action' }),
      icon: EIconValidations.AddCircle,
      eventClick: () => addActions()
    } as BaseButtonDef
  })
  /**
   * Getter for the confirmButton of the modal - Return the cancel and the add buttons
   * @returns {ConfirmButtonsDef} - The confirm buttons for the modal
   */
  const confirmButtons = computed((): ConfirmButtonsDef => {
    return {
      onCancel: exitModal,
      onConfirm: () => submitNewActions(selectedActionsToSend.value),
      confirmIcon: EIconValidations.AddCircle,
      confirmLabel: t('common.add'),
      disabledConfirm: selectedActionsNumber.value === 0
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
      disabled: selectedActionsToDeleteNumber.value === 0,
      itemList: [
        {
          icon: EIconEdit.Delete,
          name: t('common.delete'),
          disabled: selectedActionsToDeleteNumber.value === 0,
          title: t('common.deleteSelectedTitleF', { name: 'actions' }),
          eventClick: () => deleteSelectedActions()
        }
      ]
    }
  })
  // #####################################
  // METHODS
  // #####################################
  const addActions = () => {
    showAddAction.value = true
  }
  const selectActionsToAdd = (rows: string[]) => {
    selectedActionsToSend.value = rows.map((actionName: string) => {
      return getActions.value.find((action: IRoleAction) => action.title === actionName) as IRoleAction
    })
    selectedActionsNumber.value = rows.length
  }

  const selectActionsToDelete = (rows: string[]) => {
    selectedActionsToDelete.value = rows.map((actionName: string) => {
      const action = getActions.value.find((action: IRoleAction) => action.title === actionName)
      return action as IRoleAction
    })

    selectedActionsToDeleteNumber.value = rows.length
  }

  const deleteSelectedActions = () => {
    emit(
      'update:currentActions',
      props.currentActions.filter((action: IRoleAction) => {
        const userActions = selectedActionsToDelete.value.map(r => r.action)
        return !userActions.includes(action.action as string)
      })
    )
    selectActionsToDelete([])
  }

  const submitNewActions = (newActions: IRoleAction[]) => {
    const actionsToSend = [...props.currentActions]
    newActions.map(newActionToSend => {
      actionsToSend.push(newActionToSend)
    })
    emit('update:currentActions', actionsToSend)
    exitModal()
  }
  /**
   * Update route for deletion with a action id
   * @param {string} actionId - The action's id to delete
   */
  const deleteAction = async (actionId: string) => {
    actionToDelete.value = actionId
    onDeleteAction()
  }
  const onDeleteAction = () => {
    emit(
      'update:currentActions',
      props.currentActions.filter((action: IRoleAction) => action.action !== actionToDelete.value)
    )
    actionToDelete.value = undefined
    showDeleteAction.value = false
  }
  const actionsActionButton = (line: IRoleAction): BaseButtonDef[] => {
    return [
      {
        icon: EIconEdit.Delete,
        label: t('common.delete'),
        title: t('users.table.actions.delete', { name: line.name }),
        eventClick: () => deleteAction(line.action as string)
      }
    ]
  }
  /**
   * Closes the modal and reset the selected roles
   */
  const exitModal = () => {
    showAddAction.value = false
    selectedActionsNumber.value = 0
    selectedActionsToSend.value = []
  }
</script>

<template>
  <div>
    <ModalOverlay v-if="showAddAction">
      <OverlayCard
        data-testid="add-actions-card"
        :name="t(`${langPath}.addActions.title`)"
        :hasChange="() => selectedActionsNumber > 0"
        :onLastAction="exitModal"
        :onExit="exitModal"
        :confirmButtons="confirmButtons">
        <BaseTable
          data-testid="add-actions-base-table"
          class="add-actions-table"
          :columnList="actionsColumns"
          :data="availableActionsList || []"
          lineIdentifier="title"
          hasPageFeature
          localStorageKey="ACTIONS_BASE_CARD_ADD_ACTIONS_TABLE"
          @select="selectActionsToAdd" />
      </OverlayCard>
    </ModalOverlay>
    <ModalOverlay v-if="showDeleteAction">
      <ConfirmationLayout
        data-testid="delete-actions-confirmation-layout"
        :onConfirm="onDeleteAction"
        :onCancel="() => (showDeleteAction = false)"
        :primaryMessage="
          t(`users.confirmationMessageBeginning`) + ' ' + t(`users.deleteAction.confirmationMessageAction`)
        " />
    </ModalOverlay>
    <BaseCard
      data-testid="current-actions-base-card"
      :name="t('users.main.actions')"
      :headerPrimaryAction="actionsPrimaryAction"
      :headerSecondaryAction="bulkActionsButton">
      <BaseTable
        data-testid="current-actions-base-table"
        :columnList="actionsColumns"
        :data="currentActions"
        :actionColumn="actionsActionButton"
        lineIdentifier="title"
        hasPageFeature
        localStorageKey="ACTIONS_BASE_CARD_ACTIONS_TABLE"
        @select="selectActionsToDelete" />
    </BaseCard>
  </div>
</template>

<style lang="scss" scoped>
  .add-actions-table {
    max-height: 70vh;
    max-width: 70vw;
  }
</style>
