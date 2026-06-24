<script setup lang="ts">
  import { computed, onBeforeMount, ref } from 'vue'
  import { useTranslation } from 'i18next-vue'

  import BaseCard from '@ateme/cathodic-ui/src/components/containers/BaseCard.vue'
  import BubbleText from '@ateme/cathodic-ui/src/components/elements/BubbleText.vue'
  import PromiseButton from '@ateme/cathodic-ui/src/components/elements/PromiseButton.vue'
  import PasswordInput from '@ateme/cathodic-ui/src/components/inputs/PasswordInput.vue'
  import TextInput from '@ateme/cathodic-ui/src/components/inputs/TextInput.vue'
  import { EIconLinksShare } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
  import { EBubbleTextType } from '@ateme/cathodic-ui/src/interfaces/BubbleTextEnum'

  import { loginFormComposable } from './loginFormComposable'
  import { IUser, IUserError } from '../../../interfaces/Interfaces'
  import CurrentUserService from '../../../services/CurrentUserService'
  import { loginServiceUsersStore } from '../../../users/store'

  // #####################################
  // INJECT
  // #####################################
  const { t } = useTranslation()
  // -------------------
  // store
  // -------------------
  const loginServiceStore = loginServiceUsersStore()
  const { fillConfiguration, updateOwnProfile } = loginServiceStore
  // -------------------
  // options
  // -------------------
  /** Schema used for the form */
  /**
   * Path of translations for this component
   */
  const langPath: string = 'auth'
  /**
   * fake password for edit.
   */
  const fakePassword: string = 'zZ!0zzzzZ!0zzz'

  const { userSchema } = loginFormComposable()
  // #####################################
  // PROPS / EVENTS
  // #####################################
  export type FirstUpdatePasswordProps = {
    /**
     * Selected user for edit.
     */
    currentUserName?: string
    /**
     * Selected user idp name for edit.
     */
    currentUserIdpName?: string
    /**
     * Styles to apply.
     */
    styles?: object | null
  }

  const props = withDefaults(defineProps<FirstUpdatePasswordProps>(), {
    currentUserName: undefined,
    currentUserIdpName: undefined,
    styles: null
  })

  // #####################################
  // DATA
  // #####################################
  const userCurrent = ref<Partial<IUser>>({})
  const userError = ref<IUserError>({})
  const promiseButton = ref<InstanceType<typeof PromiseButton> | null>(null)
  const wrongPasswordError = ref<string | undefined>(undefined)
  // #####################################
  // HOOK
  // #####################################
  onBeforeMount(async () => {
    await fillConfiguration()
    initData()
  })

  // #####################################
  // COMPUTED
  // #####################################
  /**
   * Test if card is for edition.
   * @returns {boolean} - <true> edition, <false> creation
   */
  const hasInitialUser = computed((): boolean => {
    return !!props.currentUserName
  })
  const isPasswordExpired = computed((): boolean => {
    return CurrentUserService.isPasswordExpired()
  })
  /**
   * Disabled value of submit button.
   * @returns {boolean} <true> enabled, <false> disabled
   */
  const disabledSubmitButton = computed((): boolean => {
    return (
      !userCurrent.value.oldPassword ||
      !userCurrent.value.password ||
      !userCurrent.value.confirmPassword ||
      userCurrent.value.password === fakePassword ||
      userCurrent.value.confirmPassword === fakePassword
    )
  })

  /**
   * Test if there is a error.
   * @returns {boolean} - <true> there is a error, <false> else.
   */
  const hasError = computed((): boolean => {
    return userCurrent.value ? updateErrorInput() : false
  })

  // #####################################
  // METHODS
  // #####################################
  /**
   * Initialization of all current data.
   */
  const initData = () => {
    if (!props.currentUserName) {
      userCurrent.value = {
        username: undefined,
        password: undefined,
        confirmPassword: undefined
      }
    } else {
      userCurrent.value = {
        username: props.currentUserName,
        idp_name: props.currentUserIdpName,
        password: fakePassword,
        confirmPassword: fakePassword
      }
    }
  }

  /**
   * Test input fields and update errors.
   * @returns {boolean} <true> there is an error, <false> otherwise.
   */
  const updateErrorInput = (): boolean => {
    userError.value = {}
    wrongPasswordError.value = undefined

    if (userCurrent.value?.password !== userCurrent.value?.confirmPassword) {
      userError.value.confirmPassword = t(`${langPath}.errors.passwordsMatch`)
    }
    const passwordPattern = userSchema.value.properties?.password?.pattern
    if (userCurrent.value?.password === userCurrent.value?.oldPassword) {
      userError.value.password = t(`${langPath}.errors.passwordMustBeDifferent`)
    } else if (userCurrent.value?.password && passwordPattern && !userCurrent.value?.password.match(passwordPattern)) {
      userError.value.password = t(`${langPath}.errors.wrongFormat`)
    }
    return Object.keys(userError.value).length > 0
  }

  /**
   * Event of submit.
   */
  const validateAndSubmit = async () => {
    let newUser: Partial<IUser> = {}
    wrongPasswordError.value = undefined
    if (hasInitialUser.value) {
      newUser = {
        username: props.currentUserName,
        oldPassword: userCurrent.value.oldPassword,
        idp_name: userCurrent.value.idp_name,
        newPassword: fakePassword !== userCurrent.value.password ? userCurrent.value.password : undefined
      }

      await updateOwnProfile(newUser).catch(() => {
        wrongPasswordError.value = t(`${langPath}.errors.wrongPassword`)
        throw new Error(wrongPasswordError.value)
      })
    }
  }
  /**
   * Event of press key enter.
   */
  const onkeyEnter = () => {
    promiseButton?.value?.$el?.click()
  }
</script>

<template>
  <div class="first-update-password">
    <BaseCard
      data-testid="login-form"
      name=""
      :style="props.styles"
      class="login-form">
      <div class="first-update-password-header">
        <slot name="header"></slot>
      </div>
      <div class="first-update-password-project-name">
        <BubbleText
          v-if="isPasswordExpired"
          data-testid="password-expired-bubble-text"
          :label="t(`${langPath}.pwdExpired`)" />
        <BubbleText
          v-else
          data-testid="temporary-password-message"
          :label="t(`${langPath}.tmpPwd`)" />
      </div>
      <form>
        <div
          class="new-user-class"
          @keyup.enter="onkeyEnter">
          <TextInput
            v-model="userCurrent.username"
            data-testid="username"
            :disabled="hasInitialUser"
            :errors="userError.username ? [userError.username as string] : undefined"
            :title="t(`${langPath}.username`)"
            autocomplete="username"
            required />
          <PasswordInput
            v-model="userCurrent.oldPassword"
            data-testid="old-password"
            :title="t(`${langPath}.oldPassword`)"
            required
            autocomplete="current-password" />
          <PasswordInput
            v-model="userCurrent.password"
            data-testid="new-password"
            :description="userSchema.properties.password.description"
            :title="t(`${langPath}.changePassword`)"
            :errors="userError.password ? [userError.password as string] : undefined"
            :class="{ 'margin-bottom-error': userError.password }"
            required
            autocomplete="new-password" />
          <PasswordInput
            v-model="userCurrent.confirmPassword"
            data-testid="confirm-new-password"
            :errors="userError.confirmPassword ? [userError.confirmPassword as string] : undefined"
            :class="{ 'margin-bottom-error': userError.confirmPassword }"
            :title="t(`${langPath}.passwordConfirmation`)"
            required
            autocomplete="new-password" />
        </div>
        <BubbleText
          v-if="wrongPasswordError"
          data-testid="wrong-password-error"
          :label="wrongPasswordError"
          :descriptionList="[t(`${langPath}.errors.wrongPasswordDescription`)]"
          :type="EBubbleTextType.Danger"
          hasDelete
          @delete="wrongPasswordError = undefined" />
        <div class="centered-button">
          <PromiseButton
            ref="promiseButton"
            data-testid="submit-button"
            :handler="validateAndSubmit"
            :disabled="hasError || disabledSubmitButton"
            :icon="EIconLinksShare.Send1" />
        </div>
      </form>
    </BaseCard>
  </div>
</template>

<style lang="scss" scoped>
  .first-update-password {
    width: 100vw;
    height: 100vh;
    overflow: hidden;
    background-color: var(--left-menu-scroll-element-thumb-background-color);
    display: flex;
    justify-content: center;
    align-items: center;
    .login-form {
      width: 28em;
      .centered-button {
        margin-top: var(--spacing-base);
        display: flex;
        justify-content: center;
      }
    }
  }
</style>
