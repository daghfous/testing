<script setup lang="ts">
  import { notificationStore } from '@ateme/cathodic-ui/src/components/notifications/notificationStore.ts'
  import { storeToRefs } from 'pinia'
  import { computed, onBeforeMount } from 'vue'
  import { useTranslation } from 'i18next-vue'
  import { useRouter } from 'vue-router'
  import { IRole } from '@interfaces/Interfaces.ts'

  import { rolesStore } from '@store/allStoreDefinition.ts'
  import ConfirmationLayout from '@ateme/cathodic-ui/src/components/layouts/ConfirmationLayout.vue'
  import { rolesLink } from '../../../components/roles/router'
  // #####################################

  // INJECT
  // #####################################
  const { notifyError } = notificationStore()
  // -------------------
  // Router
  // -------------------
  const router = useRouter()
  // -------------------
  // i18n
  // -------------------
  const { t } = useTranslation()
  // -------------------
  // store
  // -------------------
  const storeRoles = rolesStore()
  const { deleteRoles } = storeRoles
  const { fillRoles } = storeRoles
  const { getAllRoles } = storeToRefs(storeRoles)
  const langPath: string = 'users'
  // #####################################
  // PROPS / EVENTS
  // #####################################
  export type rolesDeleteProps = {
    /**
     * Array of select roles.
     */
    selectedRoles: string
  }

  const props = withDefaults(defineProps<rolesDeleteProps>(), {})
  onBeforeMount(async () => {
    await fillRoles()
  })
  // #####################################
  // COMPUTED
  // #####################################
  /**
   * Detect if selection is multiple
   * @returns {number} - number of roles to delete
   */
  const getNumberOfRolesToDelete = computed((): number => {
    return props.selectedRoles.split('~').length
  })
  /**
   * getter of selected name of the first role to delete
   */
  const selectedName = computed(() => {
    if (!isMultiSelection.value && getAllRoles.value) {
      const selected = getAllRoles.value.filter((item: IRole) => item.id === props.selectedRoles)
      if (Array.isArray(selected) && selected.length > 0) {
        return selected[0].title
      } else {
        return props.selectedRoles
      }
    }
    return props.selectedRoles
  })
  /**
   * Detect if selection is multiple
   * @returns {boolean} - <true> if multiple , <false> else
   */
  const isMultiSelection = computed((): boolean => {
    return getNumberOfRolesToDelete.value > 1
  })
  /**
   * Computes delete confirmation message with role name to delete
   * @returns {string} message
   */
  const deleteConfirmationMessage = computed((): string => {
    return isMultiSelection.value
      ? `Are you sure you want to delete ${getNumberOfRolesToDelete.value} selected roles?`
      : `Are you sure you want to delete "${selectedName.value}"?`
  })

  // #####################################
  // METHODS
  // #####################################
  /**
   * Event on confirm action.
   */
  const deleteRole = async () => {
    try {
      await deleteRoles(props.selectedRoles.split('~'))
      router.back()
    } catch (error) {
      notifyError(t(`${langPath}.errors.deleteRole`))
      router.back()
      throw error
    }
  }
</script>

<template>
  <ConfirmationLayout
    data-testid="roles-delete-modal"
    :primaryMessage="deleteConfirmationMessage"
    :confirmLabel="t(`users.confirmCard.confirmLabel`)"
    :cancelLabel="t(`users.confirmCard.cancelLabel`)"
    :onCancel="() => router.push(rolesLink.path)"
    async
    @confirm="deleteRole" />
</template>
