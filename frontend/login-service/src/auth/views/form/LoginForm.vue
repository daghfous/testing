<script setup lang="ts">
  import BaseCard from '@ateme/cathodic-ui/src/components/containers/BaseCard.vue'
  import BaseLoader from '@ateme/cathodic-ui/src/components/elements/BaseLoader.vue'
  import BubbleText from '@ateme/cathodic-ui/src/components/elements/BubbleText.vue'
  import PromiseButton from '@ateme/cathodic-ui/src/components/elements/PromiseButton.vue'
  import PasswordInput from '@ateme/cathodic-ui/src/components/inputs/PasswordInput.vue'
  import SelectInput from '@ateme/cathodic-ui/src/components/inputs/SelectInput.vue'
  import TextInput from '@ateme/cathodic-ui/src/components/inputs/TextInput.vue'
  import { EBubbleTextType } from '@ateme/cathodic-ui/src/interfaces/BubbleTextEnum'
  import { EColor } from '@ateme/cathodic-ui/src/interfaces/CathodicStyleEnum'
  import { EIconLinksShare } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
  import type { AxiosError } from 'axios'
  import { storeToRefs } from 'pinia'
  import { computed, onBeforeMount, onBeforeUnmount, onMounted, ref } from 'vue'
  import { useTranslation } from 'i18next-vue'

  import { IUser, IUserError } from '../../../interfaces/Interfaces'
  import AuthStorageService from '../../../services/AuthStorageService'
  import userComposable from '../../../users/composables/userComposable'
  import { loginServiceUsersStore } from '../../../users/store/index'
  import { clearPingInterval, langPathPing } from '../../composables/userPingComposable'
  import { authenticateModeStore, IAuthenticateMode } from '../../store/authenticateMode'

  // #####################################
  // INJECT
  // #####################################
  const { t } = useTranslation()
  // -------------------
  // store
  // -------------------
  const storeAuthenticateMode = authenticateModeStore()
  const store = loginServiceUsersStore()
  const { getPing } = storeToRefs(store)
  const { fillCurrentUserInfo, userPing } = store
  // -------------------
  // options
  // -------------------
  /**
   * Path of translations for this component
   */
  const langPath: string = 'auth.login.form'

  // #####################################
  // PROPS / EVENTS
  // #####################################
  export type LoginFormProps = {
    /**
     * A promise function with login request
     */
    login?: (...args: unknown[]) => Promise<unknown>
    /**
     * A promise function with login with saml request
     */
    loginWithSaml?: (...args: unknown[]) => Promise<unknown>
    /**
     * Function used to confirm login of the user after a connection to an idp
     */
    logUser?: (...args: unknown[]) => Promise<unknown>
    /**
     * Action to execute after successful login
     */
    afterLoginSuccessed: (...args: unknown[]) => Promise<unknown>
  }

  const props = withDefaults(defineProps<LoginFormProps>(), {
    login: () => Promise.resolve(),
    loginWithSaml: () => Promise.resolve(),
    logUser: () => Promise.resolve(),
    afterLoginSuccessed: () => Promise.resolve()
  })
  const fakePassword: string = 'zZ!0zzzzZ!0zzz'

  // #####################################
  // DATA
  // #####################################
  const userCurrent = ref<Partial<IUser>>({})
  const userError = ref<IUserError>({})
  const labelLoginError = ref<string>()
  const timeRemaining = ref<number>()
  const errorMessage = ref<string>()
  const NOT_FOUND_STATUS: number = 404
  const INVALID_LOGIN: number = 400
  const INVALID_CREDENTIALS_STATUS: number = 401
  const FORBIDDEN_STATUS: number = 403
  const INVALID_LOGIN_STATUS: number[] = [NOT_FOUND_STATUS, INVALID_LOGIN, INVALID_CREDENTIALS_STATUS]
  const username = ref<HTMLInputElement | null>(null)
  const promiseButton = ref<InstanceType<typeof PromiseButton> | null>(null)
  const ping = ref<boolean>(false)
  const interval = ref<number | null>(null)

  // #####################################
  // HOOK
  // #####################################
  onBeforeMount(async () => {
    initLabelError()

    await storeAuthenticateMode.getAuthenticateModes()
    initData()
  })

  onMounted(async () => {
    await pingUserManagement()
    if (!interval.value) interval.value = setInterval(pingUserManagement, 5000) as unknown as number
    const usernameInput = document.querySelector(
      '[data-testid="text-input-login-form-login-username-text-input-input"]'
    ) as HTMLInputElement | null
    if (usernameInput) {
      usernameInput.focus()
    }
    if (AuthStorageService.getFromCookies('saml_error')) {
      errorMessage.value = AuthStorageService.getFromCookies('saml_error')
      AuthStorageService.deleteCookies(['saml_error'])
    }
    if (AuthStorageService.getFromCookies('access_token')) {
      await props.logUser(
        AuthStorageService.getFromCookies('access_token'),
        AuthStorageService.getFromCookies('refresh_token'),
        AuthStorageService.getFromCookies('username'),
        props.afterLoginSuccessed
      )
    }
  })

  onBeforeUnmount(() => {
    if (interval.value) clearInterval(interval.value)
  })

  // #####################################
  // COMPUTED
  // #####################################

  /**
   * Get submit button labels
   * @returns {Array<string>} labels
   */
  const submitButtonLabels = computed((): [string, string, string, string] => {
    return [
      t(`${langPath}.login`),
      t(`${langPath}.loggingIn`),
      t(`${langPath}.logged`),
      labelLoginError.value as string
    ]
  })
  /**
   * Disabled value of submit button.
   * @returns {boolean} <true> enabled, <false> disabled
   */
  const disabledSubmitButton = computed((): boolean => {
    let deny = true
    // If password is not updated, all others fields has to be compared to detect changes
    deny = !userCurrent.value.password || !userCurrent.value.login
    if (userComposable.isSamlUser(userCurrent.value.idp_name as string)) deny = false
    return deny
  })

  // #####################################
  // METHODS
  // #####################################
  const pingUserManagement = async () => {
    await userPing()
    ping.value = getPing.value
  }

  /**
   * Init label error with wrong username or password message
   */
  const initLabelError = () => {
    labelLoginError.value = t(`${langPath}.wrongUserNameOrPassword`)
  }
  /**
   * Initialization of all current data.
   */
  const initData = () => {
    // init with first one if only one mode exists
    const authModes: IAuthenticateMode[] = userComposable.authenticationModes()
    if (!AuthStorageService.getFromLocalStorage('loginMode')) {
      if (authModes.length === 1) AuthStorageService.addToLocalStorage('loginMode', authModes[0].name as string)
      else if (authModes.length > 1) AuthStorageService.addToLocalStorage('loginMode', 'ldap')
    }
    const currentUser: Partial<IUser> = {
      login: undefined,
      password: undefined,
      idp_name: AuthStorageService.getFromLocalStorage('lastIdpSelected') || 'local',
      mode: AuthStorageService.getFromLocalStorage('loginMode') as string,
      domain: AuthStorageService.getFromLocalStorage('ldapDomain') as string
    }

    //If idp does not exists, set it to local
    if (!userComposable.getIdpFromIdpName(AuthStorageService.getFromLocalStorage('lastIdpSelected') as string)) {
      currentUser.idp_name = 'local'
    }
    userCurrent.value = currentUser

    userError.value = {
      login: undefined,
      password: undefined,
      mode: undefined,
      domain: undefined
    }
  }

  /**
   * Event of submit.
   */
  const validateAndSubmit = async () => {
    initLabelError()
    const user = {
      login: userCurrent.value.login,
      password: fakePassword !== userCurrent.value.password ? userCurrent.value.password : undefined,
      idp_name: userCurrent.value.idp_name
    }
    try {
      if (userComposable.isSamlUser(userCurrent.value.idp_name as string)) {
        const samlUser = userComposable.getIdpFromIdpName(user.idp_name as string)
        AuthStorageService.addToLocalStorage('currentSamlName', user.idp_name as string)
        await props.loginWithSaml(samlUser)
      } else {
        await props.login(user, () => {
          clearPingInterval()
          fillCurrentUserInfo().then(() => {
            props.afterLoginSuccessed()
          })
        })
      }
    } catch (errorResponse: unknown) {
      const error = errorResponse as AxiosError
      const status: number | undefined = error?.response?.status
      const data: string = error?.response?.data as string

      // Message from user management is a sentence containing the number in seconds.
      // https://stackoverflow.com/questions/10003683/how-can-i-extract-a-number-from-a-string-in-javascript
      // Didn't display as is to allow translation
      timeRemaining.value =
        status === FORBIDDEN_STATUS && data !== 'Access denied'
          ? ((data.match(/\d+/) as RegExpMatchArray)[0] as unknown as number)
          : 0

      if (!INVALID_LOGIN_STATUS.includes(status as number)) {
        labelLoginError.value = t(`${langPath}.serverError`)
      }
      if (status == FORBIDDEN_STATUS && data == 'Access denied') {
        labelLoginError.value = t(`${langPath}.accessDenied`)
      }
      throw error
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
  <div class="login-page">
    <BaseCard
      name=""
      class="login-form">
      <div class="login-form-header">
        <slot name="header"></slot>
      </div>
      <div
        v-if="!ping"
        data-testid="communication-error"
        class="communication-error">
        <p
          class="message"
          data-testid="communicate">
          {{ t(`${langPathPing}.communicate`) }}
        </p>
        <p
          data-testid="please-wait"
          class="message">
          {{ t(`${langPathPing}.pleaseWait`) }}
        </p>
        <BaseLoader :color="EColor.ClassicGreyGrey3" />
      </div>
      <form v-else>
        <BubbleText
          v-if="errorMessage"
          data-testid="login-form-error-message"
          :type="EBubbleTextType.Danger"
          :label="errorMessage" />
        <div
          class="new-user-class"
          @keyup.enter="onkeyEnter">
          <SelectInput
            v-if="userComposable.readableAuthenticateModes().length > 1"
            v-model="userCurrent.idp_name"
            data-testid="mode-selection"
            :options="userComposable.readableAuthenticateModes() as unknown as any[]"
            title="Mode"
            required></SelectInput>
          <TextInput
            v-if="!userComposable.isSamlUser(userCurrent.idp_name as string)"
            ref="username"
            v-model="userCurrent.login"
            data-testid="username"
            :errors="userError.login ? [userError.login] : undefined"
            class="input-fields"
            title="Username"
            autocomplete="username"
            required />
          <div v-if="!userComposable.isSamlUser(userCurrent.idp_name as string)">
            <PasswordInput
              v-model="userCurrent.password"
              data-testid="password"
              :errors="userError.password ? [userError.password] : undefined"
              autocomplete="new-password"
              title="Password"
              required></PasswordInput>
          </div>
          <span v-if="timeRemaining">{{ t(`${langPath}.timeRemaining`, { seconds: timeRemaining }) }}</span>

          <div class="centered-button">
            <PromiseButton
              ref="promiseButton"
              data-testid="submit-button"
              :handler="validateAndSubmit"
              :disabled="disabledSubmitButton"
              :afterSubmit="afterLoginSuccessed"
              :notifyLeave="false"
              :labels="submitButtonLabels"
              :icon="EIconLinksShare.Send1" />
          </div>
        </div>
      </form>
    </BaseCard>
  </div>
</template>

<style lang="scss" scoped>
  .login-page {
    width: 100vw;
    height: 100vh;
    background-color: var(--left-menu-scroll-element-thumb-background-color);
    display: flex;
    justify-content: center;
    align-items: center;
    .login-form {
      width: 25em;
      .centered-button {
        margin-top: var(--spacing-base);
        display: flex;
        justify-content: center;
      }
    }
  }
</style>
