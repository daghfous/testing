<script setup lang="ts">
  import { IEntity } from '@ateme/cathodic-ui/src/interfaces/PageHeader'
  import BooleanInput from '@ateme/cathodic-ui/src/components/inputs/BooleanInput.vue'
  import BaseCard from '@ateme/cathodic-ui/src/components/containers/BaseCard.vue'
  import type { PromiseButtonDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons.d.ts'
  import PasswordInput from '@ateme/cathodic-ui/src/components/inputs/PasswordInput.vue'
  import TextInput from '@ateme/cathodic-ui/src/components/inputs/TextInput.vue'
  import ConfirmationLayout from '@ateme/cathodic-ui/src/components/layouts/ConfirmationLayout.vue'
  import TemplateView from '@ateme/cathodic-ui/src/components/template/TemplateView.vue'
  import { type StoreGeneric, storeToRefs } from 'pinia'
  import { computed, onMounted, ref, watchEffect } from 'vue'
  import ModalOverlay from '@ateme/cathodic-ui/src/components/containers/ModalOverlay.vue'

  import { useTranslation } from 'i18next-vue'
  import { useRouter } from 'vue-router'
  import type { BreadCrumbsDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/breadCrumbs.d.ts'
  import get from 'lodash/get'
  import isEqual from 'lodash/isEqual'
  import { useAuthenticateModeStore } from '@store/authenticateModeStore'
  import { IUser } from '@ateme/login-service/src/interfaces/Interfaces.ts'
  import schema from '@ateme/login-service/src/users/config/UserInput.json'
  import { usersLink } from '../router/index'
  import { useUsersManagement } from '../../../components/users/composables/usersComposable'
  import { IRole, IUnknownObjectKeys } from '@interfaces/Interfaces'
  import { notificationStore, rolesStore } from '@store/allStoreDefinition.ts'
  import { loginServiceStore } from '@store/loginServiceStore.ts'
  import { usersStore } from '../../../components/users/store'
  import RolesBaseCard from '../../common/RolesBaseCard.vue'
  import RouteConfirm from '../../common/RouteConfirm.vue'
  import BaseLoader from '@ateme/cathodic-ui/src/components/elements/BaseLoader.vue'
  import { configurationsStore } from '../../preferences/store'
  import { compareObjects } from '../../../utils/commonFunctions'
  import useUserPermissions from '../../../abilities/access/userAccessComposable'
  import type { BaseButtonDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons'
  import { EIconOtherDevice, EIconValidations } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum.ts'

  // -------------------
  // i18n
  // -------------------
  const { t } = useTranslation()
  // -------------------
  // Router
  // -------------------
  const router = useRouter()
  // -------------------
  // store
  // -------------------
  const storeUsers = usersStore()
  const { getUsers } = storeToRefs(storeUsers)
  const { fillUsers, create, edit, isThisUserTheFirstAdmin } = storeUsers
  const storeRoles = rolesStore()
  const { getAllRoles } = storeToRefs(storeRoles)
  const { fillRoles } = storeRoles
  const storeLoginService = loginServiceStore()
  const { fillCurrentUserInfo, updateOwnProfile } = storeLoginService
  const { getIsAdmin, getCurrentUser } = storeToRefs(storeLoginService as StoreGeneric)
  const { notifyError } = notificationStore()
  const confStore = configurationsStore()
  const { fillTimeoutConfiguration } = confStore

  // #####################################
  // PROPS / EVENTS
  // #####################################
  export type AddEditUserProps = {
    /**
     * Selected idp for edit.
     */
    initialUser?: string
  }

  const props = defineProps<AddEditUserProps>()
  // -------------------
  // options
  // -------------------
  /**
   * fake password for edit.
   */
  const langPath: string = 'users.main.create'

  const { isLdapUser, isSamlUser, isCurrentUserAdmin, userSchema } = useUsersManagement()
  const { canViewUsers } = useUserPermissions()

  // #####################################
  // DATA
  // #####################################
  const entity = ref<IEntity>(usersLink)
  const currentUser = ref<Partial<IUser>>({
    username: undefined,
    password: undefined,
    confirmPassword: undefined,
    idp_name: 'local',
    roles: [],
    session_timeout_disabled: false,
    level: 0
  })
  const currentRoles = ref<IRole[]>([])
  const userModel = ref<Partial<IUser>>({
    username: undefined,
    password: undefined,
    confirmPassword: undefined,
    idp_name: 'local',
    roles: [],
    session_timeout_disabled: false,
    level: 0
  })
  const userError = ref<IUnknownObjectKeys>({
    username: undefined,
    password: undefined,
    confirmPassword: undefined,
    idp_name: undefined,
    level: undefined
  })
  const submitted = ref<boolean>(false)
  const mustConfirm = ref<boolean>(false)
  const isMe = ref<boolean>(window.location.href.endsWith('update/me'))
  const editMode = ref<boolean>(!!props.initialUser || isMe.value)
  const isTheFirstAdmin = ref<boolean>(false)
  const loading = ref<boolean>(true)
  const firstLoginAlreadySet = ref<boolean>(false)
  const submitButtonLabels: [string, string, string, string] = [
    t('common.save'),
    t('common.saving'),
    t('common.saved'),
    t('common.cantSave')
  ]

  /**
   * @description Button to cancel the role edition/creation, make the user returns to the roles list view
   */
  const cancelButton: BaseButtonDef = {
    icon: EIconValidations.ClearCircle,
    label: t('common.cancel'),
    title: t('common.cancel'),
    eventClick: () => router.push(usersLink.path)
  }
  // #####################################
  // HOOK
  // #####################################
  onMounted(async () => {
    await fillTimeoutConfiguration(true)
    if (canViewUsers.value) {
      await fillUsers()
    }
    await fillCurrentUserInfo()
    if (window.location.href.endsWith('update/me')) {
      currentUser.value = getCurrentUser.value as IUser
      currentUser.value.password = undefined
      currentUser.value.confirmPassword = undefined
      currentUser.value.oldPassword = ''
      isMe.value = true
      userModel.value = { ...currentUser.value }
    }
    if (props.initialUser) {
      editMode.value = true
      currentUser.value =
        getUsers.value?.find((user: IUser) => `${user.idp_name}:${user.username}` === props.initialUser) ||
        ({} as IUser)
      await fillRoles()
      currentRoles.value = getRolesFromIds(currentUser.value.roles || [])
      currentUser.value.password = undefined
      currentUser.value.confirmPassword = undefined
      userModel.value = { ...currentUser.value }
    }
    isTheFirstAdmin.value = await isThisUserTheFirstAdmin(currentUser.value.username as string)

    await useAuthenticateModeStore().getAuthenticateModes()
    loading.value = false
  })

  // #####################################
  // COMPUTED
  // #####################################
  const submitButton = computed((): PromiseButtonDef => {
    return {
      disabled: hasError.value || !hasChanged(),
      title: t('common.save'),
      labels: submitButtonLabels,
      icon: EIconOtherDevice.Save,
      handler: async () => await validateAndSubmit()
    }
  })

  const hasError = computed(() => {
    return currentUser.value ? updateErrorInput() : false
  })

  const hasPendingChanges = computed((): boolean => {
    return Object.keys(compareObjects(currentUser.value, userModel.value)).length !== 0 && !submitted.value
  })
  // #####################################
  // METHODS
  // #####################################

  /**
   * Get roles from ids.
   * @param {string[]} ids - List of ids on the user to edit
   * @returns {IRole[]} - List of roles from ids used for display in table.
   */
  const getRolesFromIds = (ids: string[]): IRole[] => {
    return getAllRoles.value.filter((role: IRole) => ids.includes(role.id as string)) || []
  }
  const breadCrumbs = computed((): BreadCrumbsDef => {
    const elementList = [
      entity.value.name,
      editMode.value || isMe.value
        ? t('common.editWithName', { name: currentUser.value.username })
        : t(`${langPath}.addNewUser`)
    ]
    return {
      id: 'create-update-user',
      elementList: elementList,
      routerPushHandler: event => {
        // Can only click on deployed apps
        if (event.length === 1) {
          router.push('/users')
        }
      }
    } as BreadCrumbsDef
  })
  /**
   * Test input fields and update errors.
   * @returns {boolean} <true> there is an error, <false> else.
   */
  const updateErrorInput = (): boolean => {
    userError.value = {}
    if (submitted.value) return false

    // Do not validate LDAP or SAML users
    if (isLdapUser(currentUser.value.idp_name) || isSamlUser(currentUser.value.idp_name)) {
      return false
    }

    Object.keys(currentUser.value).forEach(key => {
      const schemaKey = key as keyof typeof userSchema.value.properties
      const userKey = key as keyof typeof currentUser.value

      if (schemaKey === 'username' || schemaKey === 'password') {
        const property = userSchema.value.properties[schemaKey]

        // In edit/update mode password is optional – only validate if something was typed
        if (schemaKey === 'password' && (editMode.value || isMe.value) && !currentUser.value[userKey]) {
          return
        }

        if (userSchema.value.required.includes(schemaKey) && !currentUser.value[userKey]) {
          userError.value[schemaKey] = [t('users.errors.required')]
        } else if (
          property.pattern &&
          typeof currentUser.value[userKey] === 'string' &&
          !(currentUser.value[userKey] as string).match(property.pattern)
        ) {
          userError.value[schemaKey] = [t('users.errors.invalidFormat')]
        }
      }
    })

    if (isMe.value) {
      const anyPasswordFieldFilled =
        currentUser.value.oldPassword || currentUser.value.password || currentUser.value.confirmPassword
      if (anyPasswordFieldFilled) {
        if (!currentUser.value.oldPassword) {
          userError.value.oldPassword = [t('users.errors.required')]
        }
        if (!currentUser.value.password) {
          userError.value.password = [t('users.errors.required')]
        }
        if (!currentUser.value.confirmPassword) {
          userError.value.confirmPassword = [t('users.errors.required')]
        }
        if (!isEqual(currentUser.value.password, currentUser.value.confirmPassword)) {
          userError.value.confirmPassword = [t('users.errors.passwordsMatch')]
        }
        const passwordPattern = get(schema.properties, 'password.pattern')
        if (isEqual(currentUser.value.password, currentUser.value.oldPassword)) {
          userError.value.password = [t('users.errors.passwordMustBeDifferent')]
        } else if (
          currentUser.value.password &&
          passwordPattern &&
          !get(currentUser.value, 'password', '').match(passwordPattern)
        ) {
          userError.value.password = [t('users.errors.wrongFormat')]
        }
      }
    }

    // Password match – only when at least one field has been filled
    if (
      (currentUser.value.password || currentUser.value.confirmPassword) &&
      currentUser.value.password !== currentUser.value.confirmPassword
    ) {
      userError.value.confirmPassword = [t('users.errors.passwordsMatch')]
    }

    // Check username unicity
    if (
      !props.initialUser &&
      !isMe.value &&
      getUsers.value?.some(
        (user: IUser) => user.username === currentUser.value.username && user.idp_name === currentUser.value.idp_name
      )
    ) {
      userError.value.username = [t(`${langPath}.userAlreadyExists`)]
    }
    return Object.keys(userError.value).length > 0
  }

  /**
   * Check whether the user has entered a new password.
   * @returns {boolean} - <true> a password value is present, <false> otherwise.
   */
  const isPasswordEntered = (): boolean => {
    return !!currentUser.value?.password
  }
  /**
   * Validate form inputs then submit the create / edit request.
   *
   * - In **create** mode: builds the full user payload and calls {@link create}.
   * - In **self-update** mode (`isMe`): delegates to {@link updateOwnProfile} which only
   *   patches the password when new credentials have been provided.
   * - In **admin-edit** mode (`props.initialUser`): builds a diff against the original
   *   {@link userModel} and only sends the fields that have actually changed, plus
   *   `newPassword` when a new password has been entered.
   * @returns {Promise<void>}
   */
  const validateAndSubmit = async (): Promise<void> => {
    if (hasError.value) {
      notifyError(t(`${langPath}.cantCreateUser`))
      return
    }
    if (currentUser.value.session_timeout_disabled && !mustConfirm.value) {
      mustConfirm.value = true
      return
    }

    submitted.value = true

    if (!props.initialUser) {
      // ---- Create or self-update ----
      const newUser: Partial<IUser> = {
        ...currentUser.value,
        roles: currentUser.value.roles
      }
      if (newUser.idp_name === 'local') {
        delete newUser.idp_name
      }
      if (isMe.value) {
        await updateOwnProfile(newUser)
      } else {
        await create(newUser)
          .then(() => {
            router.push(usersLink.path)
          })
          .catch(() => {
            notifyError(t(`${langPath}.cantCreateUser`))
          })
      }
    } else {
      // ---- Admin edit: only send changed fields ----
      const changedData: Partial<IUser> = {
        username: currentUser.value.username,
        idp_name: currentUser.value.idp_name
      }

      const fieldsToTrack: (keyof IUser)[] = [
        'roles',
        'session_timeout_disabled',
        'password_expiration_disabled',
        'first_login',
        'level'
      ]
      fieldsToTrack.forEach(field => {
        if (!isEqual((currentUser.value as IUser)[field], (userModel.value as IUser)[field])) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          ;(changedData as any)[field] = (currentUser.value as IUser)[field]
        }
      })

      if (!isLdapUser(currentUser.value.idp_name) && !isSamlUser(currentUser.value.idp_name)) {
        if (isPasswordEntered()) {
          changedData.newPassword = currentUser.value.password
        }
      }

      await edit(changedData)
        .then(() => {
          router.push(usersLink.path)
        })
        .catch(() => {
          notifyError(t(`${langPath}.cantUpdateUser`))
        })
    }
  }

  const hasChanged = (): boolean => {
    return JSON.stringify(userModel.value) !== JSON.stringify(currentUser.value) && !submitted.value
  }

  const handleRolesUpdate = (roles: IRole[]) => {
    currentRoles.value = roles
    currentUser.value.roles = roles.map(role => role.id as string)
  }

  watchEffect(() => {
    if (
      !loading.value &&
      currentUser.value.password &&
      currentUser.value.confirmPassword &&
      !userModel.value.first_login &&
      !firstLoginAlreadySet.value
    ) {
      currentUser.value.first_login = true
      firstLoginAlreadySet.value = true
    }
  })
</script>
<template>
  <TemplateView
    data-testid="create-user-view"
    :entity="entity"
    :headerPrimaryAction="submitButton"
    :headerSecondaryAction="cancelButton"
    :breadCrumbsProps="breadCrumbs">
    <ModalOverlay v-if="mustConfirm">
      <ConfirmationLayout
        data-testid="update-profile-modal-title"
        :onConfirm="validateAndSubmit"
        :onCancel="() => (mustConfirm = false)"
        :primaryMessage="t(`users.main.confirmUserSession`)" />
    </ModalOverlay>
    <RouteConfirm :hasPendingChanges="hasPendingChanges"></RouteConfirm>
    <div
      v-if="!loading"
      class="base-cards">
      <BaseCard
        data-testid="users-general-base-card"
        :name="t('users.main.general')">
        <form
          class="general-user-information-form"
          @keyup.enter="validateAndSubmit">
          <TextInput
            v-if="editMode && !isMe"
            v-model="currentUser.idp_name"
            data-testid="user-idp-name"
            :description="t('users.inputs.idp_name.description')"
            :title="t('users.inputs.idp_name.title')"
            :disabled="editMode" />
          <TextInput
            v-model="currentUser.username"
            data-testid="user-username"
            :description="t('users.inputs.username.description')"
            :errors="editMode || isMe ? undefined : userError.username"
            :title="t('users.inputs.username.title')"
            autocomplete="username"
            :disabled="editMode || isMe"
            required />
          <PasswordInput
            v-if="isMe"
            v-model="currentUser.oldPassword"
            data-testid="user-old-password"
            :title="t(`users.main.view.oldPassword`)"
            autocomplete="current-password"></PasswordInput>
          <PasswordInput
            v-model="currentUser.password"
            data-testid="user-password"
            :title="editMode ? t('users.inputs.newPassword.title') : t('users.inputs.password.title')"
            :description="userSchema.properties.password.description"
            :errors="userError.password"
            :required="!editMode && !isMe"
            autocomplete="new-password" />
          <PasswordInput
            v-model="currentUser.confirmPassword"
            data-testid="user-confirm-password"
            :description="userSchema.properties.password.description"
            :errors="userError.confirmPassword"
            :title="
              editMode ? t('users.inputs.newPasswordConfirmation.title') : t('users.inputs.passwordConfirmation.title')
            "
            :required="!editMode && !isMe"
            autocomplete="new-password" />
          <BooleanInput
            v-if="isCurrentUserAdmin && !isMe"
            v-model="currentUser.session_timeout_disabled"
            data-testid="user-disable-session-timeout"
            :title="t(`users.main.sessionDeactivation`)" />
          <BooleanInput
            v-if="getIsAdmin && !isMe"
            v-model="currentUser.password_expiration_disabled"
            data-testid="user-password-expiration-disabled"
            :title="t(`users.main.edit.passwordExpiration`)" />
          <boolean-input
            v-if="
              getIsAdmin && !isLdapUser(currentUser.idp_name) && !isSamlUser(currentUser.idp_name) && !isMe && editMode
            "
            v-model="currentUser.first_login as boolean"
            data-testid="user-edit-first-login-checkbox"
            :disabled="!isPasswordEntered() || !!userModel.first_login"
            :title="t(`users.main.edit.forceChangePassword`)" />
        </form>
      </BaseCard>
      <RolesBaseCard
        v-if="!isMe && !isTheFirstAdmin"
        :currentRolesIds="currentUser.roles || []"
        @update:currentRoles="handleRolesUpdate" />
    </div>
    <BaseLoader v-else />
  </TemplateView>
</template>
<style lang="scss" scoped>
  .general-user-information-form {
    display: flex;
    gap: 16px; /* Adjust spacing between fields */
    align-items: center; /* Align items vertically */
  }

  .base-cards {
    display: flex;
    flex-direction: column;
    gap: 16px; /* Adjust padding as needed */
  }
  .add-roles-card {
    overflow: auto;
    max-height: calc(100vh - 20px);
    max-width: calc(100vw - 20px);
    .add-roles-table {
      overflow: auto;
      max-height: 70vh;
      max-width: 70vw;
    }
  }
</style>
