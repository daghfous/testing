<script setup lang="ts">
  import HeaderProjectLogo from './HeaderProjectLogo.vue'
  import CreateAdminForm from './form/CreateAdminForm.vue'

  // #####################################
  // PROPS / EVENTS
  // #####################################
  export type CreateAdminProps = {
    /** Default admin level */
    defaultAdminLevel: number
    /** Product logo to display */
    productLoginLogo?: string
  }

  const props = withDefaults(defineProps<CreateAdminProps>(), {
    productLoginLogo: ''
  })
</script>

<template>
  <div id="login-page">
    <CreateAdminForm :defaultAdminLevel="props.defaultAdminLevel">
      <template #header>
        <HeaderProjectLogo :productLoginLogo="props.productLoginLogo" />
      </template>
    </CreateAdminForm>
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
