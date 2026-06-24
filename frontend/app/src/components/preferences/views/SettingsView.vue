<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue'
  import { saveAs } from 'file-saver'
  import { useTranslation } from 'i18next-vue'
  import { type StoreGeneric, storeToRefs } from 'pinia'
  import TemplateView from '@ateme/cathodic-ui/src/components/template/TemplateView.vue'
  import type { PromiseButtonDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons.d.ts'
  import BaseCard from '@ateme/cathodic-ui/src/components/containers/BaseCard.vue'
  import BaseButton from '@ateme/cathodic-ui/src/components/elements/BaseButton.vue'
  import { preferencesLink } from '../router'
  import { usersStore } from '../../../components/users/store'
  import { notificationStore } from '@store/allStoreDefinition.ts'
  import { loginServiceStore } from '@store/loginServiceStore.ts'
  import { EIconUploadDownload } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
  import ModalOverlay from '@ateme/cathodic-ui/src/components/containers/ModalOverlay.vue'
  import OverlayCard from '@ateme/cathodic-ui/src/components/containers/OverlayCard.vue'
  import FileInput from '@ateme/cathodic-ui/src/components/inputs/fileInput/FileInput.vue'
  import BubbleText from '@ateme/cathodic-ui/src/components/elements/BubbleText.vue'
  import BooleanInput from '@ateme/cathodic-ui//src/components/inputs/BooleanInput.vue'
  import NumberInput from '@ateme/cathodic-ui//src/components/inputs/NumberInput.vue'
  import SelectInput from '@ateme/cathodic-ui//src/components/inputs/SelectInput.vue'
  import { IUnknownObjectKeys } from '@interfaces/Interfaces.ts'
  import { ITimeoutConfiguration } from '@ateme/login-service/src/interfaces/Interfaces'
  import { configurationsStore } from '../../../components/preferences/store'
  import configurationConstants from '../../../components/preferences/constants.ts'
  import { EBubbleTextType } from '@ateme/cathodic-ui/src/interfaces/BubbleTextEnum.ts'
  import { IEntity } from '@ateme/cathodic-ui/src/interfaces/PageHeader'
  import { ISelectInputOption } from '@ateme/cathodic-ui/src/interfaces/SelectInput.ts'
  import { isDifferent } from '@ateme/cathodic-ui/src/utils/Differences.ts'

  // -------------------
  // i18n
  // -------------------
  const { t } = useTranslation()
  // -------------------
  // store
  // -------------------
  const { notifySuccess, notifyError } = notificationStore()
  const { BackupConfiguration, RestoreConfiguration } = usersStore()
  const settingsStore = configurationsStore()
  const { fillTimeoutConfiguration, updateTimeoutConfiguration } = settingsStore
  const {
    getRefreshTokenExpiration,
    getUserDeactivationPeriod,
    getMaxSuccessiveFailedLogin,
    getEnableUserDeactivation,
    getLogoutTimeout,
    getLogoutTimeoutInfiniteOptionEnabled,
    getPasswordExpiration,
    getPasswordMinLength
  } = storeToRefs(settingsStore)
  const { getIsAdmin } = storeToRefs(loginServiceStore() as StoreGeneric)
  // -------------------
  // INJECT
  // -------------------
  const usersLangPath: string = 'users.configuration.backupRestore'
  const authenticationlangPath: string = 'users.configuration.logoutSettings'
  // #####################################
  // DATA
  // #####################################
  const newFile = ref<File | null>(null)
  const error = ref<IUnknownObjectKeys | undefined>(undefined)
  const showRestoreUsers = ref<boolean>(false)
  const timeoutCurrent = ref<string>(configurationConstants.values.logoutTimeoutOptions.infinite.label)
  const refreshTokenCurrent = ref<string>('0')
  const currentEnableUserDeactivation = ref<boolean>(false)
  const currentUserDeactivationPeriod = ref<number>(0)
  const currentMaxSuccessiveFailedLogin = ref<number>(0)
  const currentPasswordExpiration = ref<number>(0)
  const currentPasswordMinLength = ref<number>(10)
  const forceChangePassword = ref<boolean>(false)
  const sessionTimeoutOptions = ref<ISelectInputOption[]>([])
  const idleTimeoutOptions = ref<ISelectInputOption[]>([])
  const currentTimeoutConfiguration = computed(
    (): ITimeoutConfiguration => ({
      logout_timeout: Number(timeoutCurrent.value),
      refresh_token_expiration: Number(refreshTokenCurrent.value),
      user_deactivation_period: currentEnableUserDeactivation.value ? currentUserDeactivationPeriod.value : -1,
      max_successive_failed_login: currentMaxSuccessiveFailedLogin.value,
      force_change_password: forceChangePassword.value,
      password_policy: {
        expiration_delay_in_days: currentPasswordExpiration.value,
        password_min_length: currentPasswordMinLength.value
      }
    })
  )
  const defaultTimeoutConfiguration = ref<ITimeoutConfiguration | undefined>(undefined)
  // #####################################
  // HOOK
  // #####################################
  onMounted(async () => {
    await fillTimeoutConfiguration()
    updateAllValues()
    sessionTimeoutOptions.value = getSessionTimeoutOptions()
    idleTimeoutOptions.value = getIdleTimeoutOptions()
  })
  // #####################################
  // COMPUTED
  // #####################################

  /**
   * update all values from store to local variables
   */
  const updateAllValues = () => {
    timeoutCurrent.value = getLogoutTimeout.value.toString()
    refreshTokenCurrent.value = getRefreshTokenExpiration.value.toString()
    currentEnableUserDeactivation.value = getEnableUserDeactivation.value
    currentUserDeactivationPeriod.value = getUserDeactivationPeriod.value
    currentMaxSuccessiveFailedLogin.value = getMaxSuccessiveFailedLogin.value
    currentPasswordExpiration.value = getPasswordExpiration.value
    currentPasswordMinLength.value = getPasswordMinLength.value
    defaultTimeoutConfiguration.value = {
      logout_timeout: Number(timeoutCurrent.value),
      refresh_token_expiration: Number(refreshTokenCurrent.value),
      user_deactivation_period: currentEnableUserDeactivation.value ? currentUserDeactivationPeriod.value : -1,
      max_successive_failed_login: currentMaxSuccessiveFailedLogin.value,
      force_change_password: forceChangePassword.value,
      password_policy: {
        expiration_delay_in_days: currentPasswordExpiration.value,
        password_min_length: currentPasswordMinLength.value
      }
    }
  }
  /**
   * Get all logout timeout options (and check if "infinite" is enabled via LOGOUT_TIMEOUT_INFINITE_OPTION).
   * @returns {Array<string>} - Timeout options.
   */
  const getSessionTimeoutOptions = (): ISelectInputOption[] => {
    const options = Object.values(configurationConstants.values.logoutTimeoutOptions)
    return options.reduce((logoutOptions: ISelectInputOption[], option: ISelectInputOption) => {
      // Check if option is NOT the "infinite" option
      if (option !== configurationConstants.values.logoutTimeoutOptions.infinite) {
        return [...logoutOptions, option]
      }

      // Handle "infinite" option conditionally
      if (getLogoutTimeoutInfiniteOptionEnabled.value) {
        return [...logoutOptions, { label: option.label, value: option.value }]
      }

      return logoutOptions
    }, [])
  }
  /**
   * Get all logout timeout options (and check if "infinite" is enabled via LOGOUT_TIMEOUT_INFINITE_OPTION).
   * @returns {Array<ITimeoutConfiguration>} - Timeout options.
   */
  const getIdleTimeoutOptions = (): ISelectInputOption[] => {
    const options = Object.values(configurationConstants.values.idleTimeoutOptions)
    return options.reduce((logoutOptions: ISelectInputOption[], option: IUnknownObjectKeys) => {
      return [...logoutOptions, { label: option.label, value: option.value }]
    }, [])
  }

  /**
   * @description Check if timeout is greater than refresh token
   * @returns {boolean} timeout is greater than refresh token
   */
  const isValid = computed((): boolean => {
    return Number(timeoutCurrent.value) <= Number(refreshTokenCurrent.value)
  })
  /**
   * Test if current user is admin.
   *@returns {boolean} - true if current user is admin, else return false.
   */
  const isCurrentUserAdmin = computed((): boolean => {
    return getIsAdmin.value
  })

  /**
   * Get description of the view
   * @returns {IEntity} object that contains description of the view
   */
  const entity = computed((): IEntity => {
    return preferencesLink
  })

  /**
   * Restore users submit button
   * @returns {PromiseButtonDef} - PromiseButtonDef object for restore users button
   */
  const restoreUsersSubmitButton = computed((): PromiseButtonDef => {
    return {
      labels: [
        t(`${usersLangPath}.restore.buttonLabels.restore`),
        t(`${usersLangPath}.restore.buttonLabels.restoring`),
        t(`${usersLangPath}.restore.buttonLabels.restored`),
        t(`${usersLangPath}.restore.buttonLabels.cannotRestore`)
      ],
      icon: EIconUploadDownload.Upload1,
      disabled: !newFile.value,
      handler: () => loadConfiguration()
    } as PromiseButtonDef
  })

  /**
   * Submit authentication configuration button
   * @returns {PromiseButtonDef} - PromiseButtonDef object for submit authentication configuration button
   */
  const submitAuthenticationConfigurationButton = computed((): PromiseButtonDef => {
    return {
      labels: [
        t('users.main.submit'),
        t(`${authenticationlangPath}.preferences.pending`),
        t(`${authenticationlangPath}.preferences.resolved`),
        t(`${authenticationlangPath}.preferences.rejected`)
      ],
      disabled: isSubmitConfigurationDisabled.value,
      handler: () => submitNewConfiguration()
    } as PromiseButtonDef
  })

  /**
   * Check if submit configuration button is disabled
   * @returns {boolean} - true if submit configuration button is disabled, else return false.
   */
  const isSubmitConfigurationDisabled = computed((): boolean => {
    return (
      !isDifferent(currentTimeoutConfiguration.value, defaultTimeoutConfiguration.value) ||
      !isValid.value ||
      currentUserDeactivationPeriod.value > 3600 ||
      currentUserDeactivationPeriod.value < -1 ||
      currentMaxSuccessiveFailedLogin.value > 10 ||
      currentMaxSuccessiveFailedLogin.value < 1 ||
      currentPasswordExpiration.value < -1 ||
      currentPasswordMinLength.value < 10 ||
      currentPasswordMinLength.value > 255
    )
  })

  //Methods
  /**
   * Handler of promise button.
   * @returns {object} - {promise, labels.}
   */
  const saveBackup = async () => {
    try {
      BackupConfiguration()
        .then((response: IUnknownObjectKeys) => {
          const fileName = response.headers['content-disposition'].split('filename=')[1].replace(/['"]+/g, '')
          const blob = new Blob([response.data], {
            type: response.headers['content-type'],
            // @ts-expect-error - response.data is a Blob
            encoding: 'UTF-8'
          })

          saveAs(blob, fileName)
          notifySuccess(t(`${usersLangPath}.backup.buttonLabels.saved`))
        })
        .catch(() => notifyError(t(`${usersLangPath}.backup.buttonLabels.cannotSave`)))
    } catch {
      notifyError(t(`${usersLangPath}.backup.buttonLabels.cannotSave`))
    }
  }

  /**
   * Updates the timeout configuration and update the default configuration with the current one
   * Used to handle correctly the submit button disabled state after the first submit
   */
  const submitNewConfiguration = async () => {
    await updateTimeoutConfiguration(currentTimeoutConfiguration.value).then(() => {
      //Only set default configuration equal to current configuration if successfully patched
      // Delete token expiration as it is not in the form
      delete currentTimeoutConfiguration.value.token_expiration
      // Set force_change_password to false as it is not send to backend
      currentTimeoutConfiguration.value.force_change_password = false
      defaultTimeoutConfiguration.value = {
        ...currentTimeoutConfiguration.value
      }
    })
  }
  /**
   * Load configuration from file.
   * @returns {Promise<void>} - Promise that resolves when configuration is loaded.
   */
  const loadConfiguration = async () => {
    try {
      const formData = new FormData()
      formData.append('data', newFile.value as File)
      RestoreConfiguration(formData)
        .then(() => notifySuccess(t(`${usersLangPath}.restore.buttonLabels.restored`)))
        .catch(() => notifyError(t(`${usersLangPath}.restore.buttonLabels.cannotRestore`)))
      showRestoreUsers.value = false
    } catch {
      notifyError(t(`${usersLangPath}.restore.buttonLabels.cannotRestore`))
      showRestoreUsers.value = false
    }
  }
  /**
   * Event of change file.
   * @param {File | null} file - File selected by user.
   */
  const onFileInput = (file: File | null) => {
    newFile.value = file
    error.value = undefined
  }

  /**
   * Exit the modal
   */
  const exitRestoreUser = () => {
    showRestoreUsers.value = false
  }
</script>

<template>
  <TemplateView
    data-testid="settings-view"
    :entity="entity"
    :headerPrimaryAction="submitAuthenticationConfigurationButton">
    <template #default>
      <ModalOverlay v-if="showRestoreUsers">
        <OverlayCard
          data-testid="restore-users-overlay-card"
          :name="t(`${usersLangPath}.restore.title`)"
          :onLastAction="exitRestoreUser"
          :onExit="exitRestoreUser"
          :headerPrimaryAction="restoreUsersSubmitButton">
          <BubbleText
            data-testid="restore-users-warning-message"
            class="restore-user-message"
            :label="t(`${usersLangPath}.restore.warningMessage`)" />
          <FileInput
            data-testid="restore-users-file-input"
            :value="newFile"
            :extensions="['zip']"
            required
            @update:modelValue="onFileInput"></FileInput>
        </OverlayCard>
      </ModalOverlay>
      <BubbleText
        v-if="!isValid"
        data-testid="session-timeout-error-message"
        class="idle-timeout-warning"
        :type="EBubbleTextType.Warning"
        :label="t(`${authenticationlangPath}.errorMessage`)" />
      <div class="grid-view">
        <BaseCard
          data-testid="backup-restore-users-card"
          :name="t(`${usersLangPath}.main.label`)"
          class="backup-restore-users">
          <BaseButton
            data-testid="backup-users-base-button"
            :eventClick="saveBackup"
            :title="t(`${usersLangPath}.main.create`)"
            :icon="EIconUploadDownload.Download1"
            class="backup-restore-button backup-button"
            :label="t(`${usersLangPath}.main.create`)" />
          <BaseButton
            data-testid="restore-users-base-button"
            :eventClick="() => (showRestoreUsers = true)"
            :title="t(`${usersLangPath}.main.restore`)"
            class="backup-restore-button"
            :icon="EIconUploadDownload.Upload1"
            :label="t(`${usersLangPath}.main.restore`)" />
        </BaseCard>
        <BaseCard
          data-testid="authentication-settings-card"
          :name="t(`${authenticationlangPath}.title`)"
          class="authentication-settings-configuration">
          <div v-if="isCurrentUserAdmin">
            <SelectInput
              v-model="timeoutCurrent"
              data-testid="idle-timeout"
              :options="idleTimeoutOptions"
              :title="t(`${authenticationlangPath}.idleTimeout.title`)"
              :description="t(`${authenticationlangPath}.idleTimeout.description`)"
              required></SelectInput>
            <SelectInput
              v-model="refreshTokenCurrent"
              data-testid="session-timeout"
              :options="sessionTimeoutOptions"
              :title="t(`${authenticationlangPath}.sessionTimeout.title`)"
              :description="t(`${authenticationlangPath}.sessionTimeout.description`)"
              :popper-container-props="{
                positionFixe: true
              }"
              required></SelectInput>
            <NumberInput
              v-model="currentMaxSuccessiveFailedLogin"
              data-testid="max-successive-fail-login"
              :description="t(`${authenticationlangPath}.maxSuccessiveFailedLogin.description`)"
              :title="t(`${authenticationlangPath}.maxSuccessiveFailedLogin.title`)"
              :max="10"
              :min="1"
              required />
            <BooleanInput
              v-model="currentEnableUserDeactivation"
              data-testid="user-deactivation"
              class="user-deactivation"
              :title="t(`${authenticationlangPath}.userDeactivation.title`)"
              :description="t(`${authenticationlangPath}.userDeactivation.description`)" />
            <NumberInput
              v-if="currentEnableUserDeactivation"
              v-model="currentUserDeactivationPeriod"
              data-testid="user-deactivation-period"
              :description="t(`${authenticationlangPath}.userDeactivationPeriod.description`)"
              :title="t(`${authenticationlangPath}.userDeactivationPeriod.title`)"
              :min="-1"
              :max="3600"
              required />
          </div>
          <div
            v-else
            id="no-admin-message">
            {{ t(`${authenticationlangPath}.noAdminMessage`) }}
          </div>
        </BaseCard>
        <BaseCard
          data-testid="authentication-settings-password-policy-card"
          :name="t(`${authenticationlangPath}.pwdPolicy.title`)"
          class="authentication-settings-password-policy">
          <div v-if="isCurrentUserAdmin">
            <NumberInput
              v-model="currentPasswordExpiration"
              data-testid="password-expiration"
              :description="t(`${authenticationlangPath}.pwdExpiration.description`)"
              :title="t(`${authenticationlangPath}.pwdExpiration.title`)"
              :min="-1"
              required />
            <NumberInput
              v-model="currentPasswordMinLength"
              data-testid="password-minimum-length-input"
              :description="t(`${authenticationlangPath}.pwdLength.description`)"
              :title="t(`${authenticationlangPath}.pwdLength.title`)"
              :min="10"
              :max="255"
              required />
            <BooleanInput
              v-model="forceChangePassword"
              data-testid="force-users-change-password-checkbox"
              :title="t(`${authenticationlangPath}.forceChangePassword.title`)"
              :description="t(`${authenticationlangPath}.forceChangePassword.description`)"></BooleanInput>
          </div>
        </BaseCard>
      </div>
    </template>
  </TemplateView>
</template>

<style lang="scss" scoped>
  .idle-timeout-warning {
    margin-bottom: var(--spacing-base);
  }
  .restore-user-message {
    margin-bottom: var(--spacing-triple-base);
  }
  .grid-view {
    display: grid;
    grid-gap: var(--spacing-base);
    .user-deactivation {
      margin-bottom: var(--spacing-double-base);
    }
    .backup-restore-users {
      grid-column: 1;
      grid-row: 1;
      .backup-restore-button {
        margin-bottom: var(--spacing-double-base);
        width: 100%;
      }
    }
    .authentication-settings-password-policy {
      grid-column: 1;
      grid-row: 2;
    }
    .authentication-settings-configuration {
      grid-column: 2;
      grid-row: 1 / 3;
    }
  }
</style>
