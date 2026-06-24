<script setup lang="ts">
  import { AxiosResponse } from 'axios'

  import HeaderProjectLogo from './HeaderProjectLogo.vue'
  import LoginForm from './form/LoginForm.vue'

  // #####################################
  // PROPS / EVENTS
  // #####################################
  export type LoginPageProps = {
    /**
     * A promise function with login request
     */
    login: () => Promise<AxiosResponse>
    /**
     * A promise function with login with saml request
     */
    loginWithSaml: () => Promise<AxiosResponse>
    /**
     * Function used to confirm login of the user after a connection to an idp
     */
    logUser: () => Promise<AxiosResponse>
    /**
     * Action to execute after successful login
     */
    afterLoginSuccessed: () => Promise<AxiosResponse>
    /** Product logo to display */
    productLoginLogo?: string
  }

  const props = withDefaults(defineProps<LoginPageProps>(), {
    productLoginLogo: ''
  })
</script>

<template>
  <div
    id="login-page"
    class="login-page">
    <LoginForm
      :login="props.login"
      :loginWithSaml="props.loginWithSaml"
      :afterLoginSuccessed="props.afterLoginSuccessed"
      :logUser="props.logUser">
      <template #header>
        <HeaderProjectLogo :productLoginLogo="props.productLoginLogo" />
      </template>
    </LoginForm>
  </div>
</template>

<style lang="scss" scoped>
  #login-page {
    height: 100%;
    text-align: center;
    width: 100%;
  }
</style>
