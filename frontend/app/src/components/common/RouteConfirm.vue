<script setup lang="ts">
  import { ref } from 'vue'
  import { useTranslation } from 'i18next-vue'
  import { onBeforeRouteLeave, type RouteLocationNormalized, useRouter } from 'vue-router'
  import ModalOverlay from '@ateme/cathodic-ui/src/components/containers/ModalOverlay.vue'
  import ConfirmationLayout from '@ateme/cathodic-ui/src/components/layouts/ConfirmationLayout.vue'

  // #####################################
  // PROPS / EVENTS
  // #####################################
  const props = defineProps<{
    hasPendingChanges: boolean
  }>()

  // -------------------
  // i18n
  // -------------------
  const { t } = useTranslation()

  // -------------------
  // Router
  // -------------------
  const router = useRouter()

  // -------------------
  // Local state
  // -------------------
  const showModal = ref<boolean>(false)
  const pendingNavigation = ref<RouteLocationNormalized | null>(null)
  const allowNavigation = ref<boolean>(false)
  const langPath: string = 'cathodicUi.components.containers.overlayCard'

  // -------------------
  // Navigation Guard
  // -------------------
  onBeforeRouteLeave(to => {
    if (allowNavigation.value) {
      return true
    }

    if (props.hasPendingChanges) {
      showModal.value = true
      pendingNavigation.value = to
      return false
    }

    return true
  })

  // #####################################
  // METHODS
  // #####################################

  const stayOnPage = () => {
    showModal.value = false
    pendingNavigation.value = null
  }

  const leavePage = () => {
    showModal.value = false
    if (pendingNavigation.value) {
      const target = pendingNavigation.value
      pendingNavigation.value = null
      allowNavigation.value = true
      router.push(target)
    }
  }
</script>
<template>
  <ModalOverlay v-if="showModal">
    <ConfirmationLayout
      data-testid="confirmation-modal-before-leave"
      :onConfirm="leavePage"
      :onCancel="stayOnPage"
      :primaryMessage="t(`${langPath}.confirmationExit.message`)" />
  </ModalOverlay>
</template>
