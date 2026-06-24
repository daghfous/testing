<script setup lang="ts">
  import { computed } from 'vue'
  import { useRouter } from 'vue-router'
  import ConfirmationLayout from '@ateme/cathodic-ui/src/components/layouts/ConfirmationLayout.vue'
  import { idpStore } from '@store/allStoreDefinition.ts'
  import { idpLink } from '../../../components/tabs'
  import { useTranslation } from 'i18next-vue'

  // #####################################
  // INJECT
  // #####################################// -------------------
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
  const { deleteIdP } = idpStore()

  // #####################################
  // PROPS / EVENTS
  // #####################################
  export type deleteIdpProps = {
    /**
     * Array of selected idp_name
     */
    idpName: string
  }

  const props = withDefaults(defineProps<deleteIdpProps>(), {})

  // #####################################
  // COMPUTED
  // #####################################
  /**
   * Computes delete confirmation message with idp domain name to delete
   * @returns {string} message
   */
  const deleteConfirmationMessage = computed((): string => {
    return `Are you sure you want to delete "${props.idpName}"?`
  })

  // #####################################
  // METHODS
  // #####################################
  /**
   * Event on confirm action.
   */
  const delIdP = async () => {
    await deleteIdP(props.idpName)
    router.back()
  }
</script>

<template>
  <ConfirmationLayout
    data-testid="idp-delete-modal"
    :primaryMessage="deleteConfirmationMessage"
    :confirmLabel="t(`users.confirmCard.confirmLabel`)"
    :cancelLabel="t(`users.confirmCard.cancelLabel`)"
    :onCancel="() => router.push(idpLink.path)"
    async
    @confirm="delIdP" />
</template>
