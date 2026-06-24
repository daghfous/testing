import { ref } from 'vue'

/**
 * Reactive flag indicating whether CASL abilities have been loaded.
 * Set to `true` once `updateAbility()` resolves in App.vue.
 * Used by views to distinguish between "abilities loading" and "access denied".
 */
export const abilitiesReady = ref(false)
