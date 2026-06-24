<script setup lang="ts">
  import InlineSvg from 'vue-inline-svg'

  // #####################################
  // INJECT
  // #####################################
  // -------------------
  // options
  // -------------------
  const logoHeight: string = '5em'

  // #####################################
  // PROPS / EVENTS
  // #####################################
  export type HeaderProjectLogoProps = {
    /** Product logo to display */
    productLoginLogo?: string
  }

  const props = withDefaults(defineProps<HeaderProjectLogoProps>(), {
    productLoginLogo: ''
  })
</script>

<template>
  <div>
    <div class="ateme-logo">
      <InlineSvg
        class="product-logo-ateme"
        src="static-um/svg/AtemeMainLogo.svg"
        :data-testid="`product-ateme-logo`"
        :height="logoHeight"
        width="11em" />
    </div>
    <InlineSvg
      :src="props.productLoginLogo"
      height="4em"
      width="16em"
      class="product-logo" />
  </div>
</template>

<style lang="scss" scoped>
  .product-logo-ateme {
    padding-bottom: 2em;
  }
  .product-logo {
    margin: -0.5em 0;
  }
</style>
