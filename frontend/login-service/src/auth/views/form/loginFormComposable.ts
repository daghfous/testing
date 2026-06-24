import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import { useTranslation } from 'i18next-vue'
import { GenericObject } from '@ateme/cathodic-ui/src/interfaces/GenericType'
import schema from '../../../users/config/UserInput.json'
import { loginServiceUsersStore } from '../../../users/store'

/**
 * @returns {object} - All login form composable utils
 */
export function loginFormComposable() {
  // #####################################
  // INJECT
  // #####################################
  const { t } = useTranslation()

  // -------------------
  // store
  // -------------------
  const store = loginServiceUsersStore()
  const { getConfiguration } = storeToRefs(store)

  // #####################################
  // COMPUTED
  // #####################################

  const userSchema = computed((): GenericObject => {
    const updatedSchema = JSON.parse(JSON.stringify(schema))
    const pattern = getConfiguration.value.password_policy?.regex_pattern

    const minLength = getConfiguration.value.password_policy?.password_min_length
    // Update pattern
    updatedSchema['properties']['password']['pattern'] = pattern?.replace('{,255}', `{${minLength},255}`)
    // Update description
    updatedSchema['properties']['password']['description'] = `${t('auth.password.description', {
      min_length: minLength
    })}`
    return updatedSchema
  })
  return {
    userSchema
  }
}
