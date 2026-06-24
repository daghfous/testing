import { storeToRefs } from 'pinia'
import { computed, ref } from 'vue'
import { useTranslation } from 'i18next-vue'
import { rolesStore } from '@store/allStoreDefinition'
import { EIcon, EIconEdit } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
/**
 *
 * @returns {unknown} - all the composable utils
 */
export function useRoleManagement() {
  // #####################################
  // INJECT
  // #####################################
  // -------------------
  // i18n
  // -------------------
  const { t } = useTranslation()
  // -------------------
  // store
  // -------------------
  const rolesStoreDef = rolesStore()
  const { setIsExpertMode } = rolesStoreDef
  const { getIsExpertMode } = storeToRefs(rolesStoreDef)
  // -------------------
  // options
  // -------------------
  /**
   * Path of translations for this component
   */
  const langPath: string = 'users.roles'
  // #####################################
  // DATA
  // #####################################
  const expertModeTitle = ref<string>(t(`${langPath}.view.modeTitle`))
  // #####################################
  // COMPUTED
  // #####################################
  const expertModeLabel = computed(() => {
    return getIsExpertMode.value ? t(`${langPath}.view.basicMode`) : t(`${langPath}.view.expertMode`)
  })

  const expertModeIcon = computed((): EIcon => {
    return getIsExpertMode.value ? EIconEdit.EyeOff : EIconEdit.Eye
  })

  // #####################################
  // METHODS
  // #####################################
  /**
   * onClick expert mode button
   */
  const clickExpertMode = () => {
    setIsExpertMode(!getIsExpertMode.value)
  }

  return {
    expertMode: getIsExpertMode,
    expertModeTitle,
    expertModeLabel,
    expertModeIcon,
    clickExpertMode
  }
}
