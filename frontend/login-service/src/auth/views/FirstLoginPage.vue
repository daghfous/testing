<script setup lang="ts">
  import { NavigationGuardNext, onBeforeRouteLeave, RouteLocationNormalized } from 'vue-router'

  import HeaderProjectLogo from './HeaderProjectLogo.vue'
  import FirstUpdatePassword from './form/FirstUpdatePassword.vue'
  import AuthStorageService from '../../services/AuthStorageService'

  // #####################################
  // PROPS / EVENTS
  // #####################################
  export type FirstLoginPageProps = {
    /**
     * Selected user for edit.
     */
    currentUserName: string
    /**
     * Selected user idp name for edit.
     */
    currentUserIdpName: string
    /** Product logo to display */
    productLoginLogo?: string
  }

  const props = withDefaults(defineProps<FirstLoginPageProps>(), {
    productLoginLogo: undefined
  })

  // #####################################
  // ROUTER
  // #####################################
  onBeforeRouteLeave((to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext) => {
    AuthStorageService.clearAuthAndUserDataFromStorages()
    next()
  })
</script>

<template>
  <div id="login-page">
    <FirstUpdatePassword
      :currentUserName="props.currentUserName"
      :currentUserIdpName="props.currentUserIdpName">
      <template #header>
        <HeaderProjectLogo :productLoginLogo="props.productLoginLogo" />
      </template>
    </FirstUpdatePassword>
  </div>
</template>

<style lang="scss" scoped>
  #login-page {
    align-items: center;
    display: flex;
    height: 100%;
    justify-content: center;
    text-align: center;
    width: 100%;

    > * {
      text-align: left;
    }
  }
</style>
