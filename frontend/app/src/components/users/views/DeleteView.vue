<script setup lang="ts">
  import { computed } from 'vue'
  import { useTranslation } from 'i18next-vue'
  import { useRouter } from 'vue-router'
  import ConfirmationLayout from '@ateme/cathodic-ui/src/components/layouts/ConfirmationLayout.vue'

  import { IUser } from '@ateme/login-service/src/interfaces/Interfaces'
  import { usersStore } from '../../../components/users/store'
  import { usersLink } from '../../users/router'

  // #####################################
  // INJECT
  // #####################################
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
  const { deleteUsers } = usersStore()
  // -------------------
  // options
  // -------------------
  /**
   * Path of translations for this component
   */
  const langPath: string = 'users'

  // #####################################
  // PROPS / EVENTS
  // #####################################
  export type usersDeleteProps = {
    /**
     * Array of select users.
     */
    selectedUsers: string
  }

  const props = defineProps<usersDeleteProps>()

  // #####################################
  // COMPUTED
  // #####################################
  /**
   * Detect if selection is multiple
   * @returns {number} - number of users to delete
   */
  const getUsersNberToDelete = computed((): number => {
    return props.selectedUsers.split('~').length
  })
  /**
   * Detect if selection is multiple
   * @returns {boolean} - <true> if multiple , <false> else
   */
  const isMultiSelection = computed((): boolean => {
    return getUsersNberToDelete.value > 1
  })
  /**
   * Computes delete confirmation message with user name to delete
   * @returns {string} message
   */
  const deleteConfirmationMessage = computed((): string => {
    return isMultiSelection.value
      ? t(`${langPath}.confirmationMessageBeginning`) +
          ` ${getUsersNberToDelete.value} ` +
          t(`${langPath}.deleteUser.confirmationMessageUsers`)
      : t(`${langPath}.confirmationMessageBeginning`) + ` "${props.selectedUsers}"?`
  })

  // #####################################
  // METHODS
  // #####################################
  /**
   * Event on confirm action.
   */
  const deleteUser = async () => {
    const usersToDelete: Partial<IUser>[] = props.selectedUsers.split('~').map((user: string): Partial<IUser> => {
      return {
        idp_name: user.split(':')[0],
        username: user.split(':')[1]
      } as IUser
    })
    await deleteUsers(usersToDelete)
    router.back()
  }
</script>

<template>
  <ConfirmationLayout
    data-testid="users-delete-modal"
    :primaryMessage="deleteConfirmationMessage"
    :confirmLabel="t(`users.confirmCard.confirmLabel`)"
    :cancelLabel="t(`users.confirmCard.cancelLabel`)"
    :onCancel="() => router.push(usersLink.path)"
    async
    @confirm="deleteUser" />
</template>
