import { ref } from 'vue'

// #####################################
// INJECT
// #####################################
// -------------------
// store
// -------------------

export const langPathPing: string = 'auth.ping.message'
// #####################################
// DATA
// #####################################
export const intervalPing = ref<number>()

// #####################################
// METHODS
// #####################################
/**
 * Clear ping interval
 */
export const clearPingInterval = () => {
  clearInterval(intervalPing.value)
  intervalPing.value = undefined
}
