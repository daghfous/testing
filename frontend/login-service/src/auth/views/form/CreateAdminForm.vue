<script setup lang="ts">
  import BaseCard from '@ateme/cathodic-ui/src/components/containers/BaseCard.vue'
  import BubbleText from '@ateme/cathodic-ui/src/components/elements/BubbleText.vue'
  import PromiseButton from '@ateme/cathodic-ui/src/components/elements/PromiseButton.vue'
  import PasswordInput from '@ateme/cathodic-ui/src/components/inputs/PasswordInput.vue'
  import TextInput from '@ateme/cathodic-ui/src/components/inputs/TextInput.vue'
  import { EBubbleTextType } from '@ateme/cathodic-ui/src/interfaces/BubbleTextEnum'
  import { EIconLinksShare } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
  import { storeToRefs } from 'pinia'
  import { computed, onBeforeMount, onBeforeUnmount, onMounted, ref } from 'vue'
  import { useTranslation } from 'i18next-vue'

  import { loginFormComposable } from './loginFormComposable'
  import { IUser, IUserError } from '../../../interfaces/Interfaces'
  import { loginServiceUsersStore } from '../../../users/store'
  import { langPathPing } from '../../composables/userPingComposable'

  // #####################################
  // INJECT
  // #####################################
  // -------------------
  // store
  // -------------------
  const store = loginServiceUsersStore()
  const { createAdmin, userPing, fillConfiguration } = store
  const { getPing } = storeToRefs(store)
  // -------------------
  // options
  // -------------------
  /**
   * fake password for edit.
   */
  const fakePassword: string = 'zZ!0zzzzZ!0zzz'
  const { t } = useTranslation()
  const { userSchema } = loginFormComposable()
  // -------------------
  // composable
  // -------------------

  // #####################################
  // PROPS / EVENTS
  // #####################################
  export type CreateAdminFormProps = {
    /** Default admin level */
    defaultAdminLevel?: number
  }

  const props = withDefaults(defineProps<CreateAdminFormProps>(), {
    defaultAdminLevel: undefined
  })

  // #####################################
  // DATA
  // #####################################
  const userCurrent = ref<Partial<IUser>>({})
  const userError = ref<IUserError>({})
  const promiseButton = ref<InstanceType<typeof PromiseButton> | null>(null)
  const username = ref<InstanceType<typeof TextInput> | null>(null)
  const ping = ref<boolean>(false)
  const interval = ref<number | null>(null)

  // #####################################
  // HOOK
  // #####################################
  onBeforeMount(() => {
    initData()
  })
  onMounted(async () => {
    await fillConfiguration()
    await pingUserManagement()
    if (!interval.value) interval.value = setInterval(pingUserManagement, 5000) as unknown as number
    if (username.value) username.value?.$el?.focus()
  })

  onBeforeUnmount(() => {
    if (interval.value) clearInterval(interval.value)
  })

  // #####################################
  // COMPUTED
  // #####################################

  /**
   * The description list of password rules
   * @returns {string[] | undefined} - The description list or undefined
   */
  const passwordDescriptionList = computed((): string[] | undefined => {
    return userSchema?.value?.properties?.password?.description.split('\n') || undefined
  })
  /**
   * Disabled value of submit button.
   * @returns {boolean} <true> enabled, <false> disabled
   */
  const disabledSubmitButton = computed((): boolean => {
    // If password is not updated, all others fields has to be compared to detect changes
    return userCurrent.value.password === fakePassword
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
  const pingUserManagement = async () => {
    await userPing()
    ping.value = getPing.value
  }
  /**
   * Initialization of all current data.
   */
  const initData = () => {
    userCurrent.value = {
      username: undefined,
      password: undefined,
      confirmPassword: undefined
    }
    userError.value = {
      username: undefined,
      duplicate: undefined,
      password: undefined,
      confirmPassword: undefined
    }
  }

  /**
   * Test input fields and update errors.
   * @returns {boolean} <true> there is an error, <false> else.
   */
  const updateErrorInput = (): boolean => {
    userError.value = {}

    if (
      userCurrent.value.username !== undefined ||
      userCurrent.value.password !== undefined ||
      userCurrent.value.confirmPassword !== undefined
    ) {
      validateUserInput()

      // Password manage.
      if (userCurrent.value.password !== userCurrent.value.confirmPassword) {
        userError.value.confirmPassword = t('auth.errors.passwordsMatch')
      }
    }

    return Object.keys(userError.value).length > 0
  }

  const validateUserInput = () => {
    ;(Object.keys(userCurrent.value) as Array<keyof IUser>).forEach(key => {
      if (key in userCurrent.value) {
        const value = userCurrent.value[key]
        const schemaProperty = userSchema.value.properties[key]

        if (schemaProperty) {
          if (userSchema.value.required.includes(key) && !value) {
            userError.value[key] = t('auth.errors.required')
          } else if (
            schemaProperty.pattern &&
            value &&
            typeof value === 'string' &&
            !new RegExp(schemaProperty.pattern).test(value)
          ) {
            userError.value[key] = t('auth.errors.invalidFormat')
          }
        }
      }
    })
  }

  /**
   * Event of submit.
   * @returns {Promise} - the notify promise.
   */
  const validateAndSubmit = (): Promise<void> => {
    const newUser: Partial<IUser> = {
      username: userCurrent.value.username,
      password: fakePassword !== userCurrent.value.password ? userCurrent.value.password : undefined
    }

    if (props.defaultAdminLevel) {
      newUser.level = props.defaultAdminLevel
    }

    return createAdmin(newUser)
  }
  /**
   * Event of press key enter.
   */
  const onkeyEnter = () => {
    promiseButton?.value?.$el?.click()
  }
</script>

<template>
  <div class="create-admin-page">
    <BaseCard
      name=""
      class="create-admin-form">
      <div class="login-form-header">
        <slot name="header"></slot>
      </div>
      <div class="login-form-project-name">
        <span>Create an admin user</span>
      </div>
      <form v-if="ping">
        <div
          class="new-user-class"
          @keyup.enter="onkeyEnter">
          <TextInput
            ref="username"
            v-model="userCurrent.username"
            data-testid="username"
            :description="userSchema.properties.username.description"
            :errors="userError.username ? [userError.username] : undefined"
            class="input-fields"
            title="Username"
            autocomplete="username"
            required />
          <PasswordInput
            v-model="userCurrent.password"
            data-testid="password"
            :title="'Password'"
            :errors="userError.password ? [userError.password] : undefined"
            autocomplete="new-password"
            required />
          <PasswordInput
            v-model="userCurrent.confirmPassword"
            data-testid="confirm-password"
            :errors="userError.confirmPassword ? [userError.confirmPassword] : undefined"
            title="Password confirmation"
            required
            autocomplete="new-password" />
          <div class="password-rules">
            <BubbleText
              v-if="passwordDescriptionList"
              data-testid="password-rules-message"
              label="Password rules"
              :descriptionList="passwordDescriptionList" />
          </div>
          <div class="centered-button">
            <PromiseButton
              ref="promiseButton"
              data-testid="submit-button"
              :handler="validateAndSubmit"
              :disabled="disabledSubmitButton || hasError"
              :icon="EIconLinksShare.Send1" />
          </div>
        </div>
      </form>
      <div
        v-else
        class="communication-error">
        <BubbleText
          data-testid="communication-error"
          :label="t(`${langPathPing}.communicate`)"
          :descriptionList="[t(`${langPathPing}.pleaseWait`)]"
          :type="EBubbleTextType.Danger" />
      </div>
    </BaseCard>
  </div>
</template>

<style lang="scss" scoped>
  .create-admin-page {
    width: 100vw;
    height: 100vh;
    background-color: var(--left-menu-scroll-element-thumb-background-color);
    display: flex;
    justify-content: center;
    align-items: center;
    .password-rules {
      position: relative;
      margin: 16px 8px 8px;
    }

    .login-form-project-name {
      display: flex;
      justify-content: center;
      margin-bottom: var(--spacing-base);
    }
    .create-admin-form {
      width: 25em;
      .centered-button {
        display: flex;
        justify-content: center;
      }
    }
  }
</style>
