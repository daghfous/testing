<script setup lang="ts">
  import { notificationStore } from '@ateme/cathodic-ui/src/components/notifications/notificationStore.ts'
  import { computed } from 'vue'
  import { useTranslation } from 'i18next-vue'
  import { useRouter } from 'vue-router'
  import { sessionsStore } from '../store'

  import { sessionsLink } from '../../../components/sessions/router'
  import ConfirmationLayout from '@ateme/cathodic-ui/src/components/layouts/ConfirmationLayout.vue'
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
  const { deleteSession } = sessionsStore()
  // -------------------
  // options
  // -------------------
  const langPath: string = 'users.sessions'
  // -------------------
  // props
  // -------------------
  export type deleteSessionProps = {
    /**
     * Selected idp for edit.
     */
    token_id: string
  }

  const props = defineProps<deleteSessionProps>()

  // #####################################
  // COMPUTED
  // #####################################
  /**
   * Computes delete confirmation message with session name to delete
   * @returns {string} message
   */
  const deleteConfirmationMessage = computed(() => t(`${langPath}.view.deleteSession`))
  // #####################################
  // METHODS
  // #####################################
  /**
   * Event on confirm action.
   */
  const onDelete = async () => {
    try {
      await deleteSession(props.token_id)
      router.push(sessionsLink.path)
    } catch (error) {
      notifyError(t(`${langPath}.errors.deleteSession`))
      router.push(sessionsLink.path)
      throw error
    }
  }
</script>

<template>
  <ConfirmationLayout
    data-testid="delete-session"
    :primaryMessage="deleteConfirmationMessage"
    :confirmLabel="t(`users.confirmCard.confirmLabel`)"
    :cancelLabel="t(`users.confirmCard.cancelLabel`)"
    :onCancel="() => router.push(sessionsLink.path)"
    async
    @confirm="onDelete" />
</template>
