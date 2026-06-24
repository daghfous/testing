<script setup lang="ts">
  import clone from 'lodash/clone'
  import cloneDeep from 'lodash/cloneDeep'
  import join from 'lodash/join'
  import map from 'lodash/map'
  import { storeToRefs } from 'pinia'
  import { computed, onBeforeMount, onBeforeUnmount, ref } from 'vue'
  import { useTranslation } from 'i18next-vue'
  import { useRouter } from 'vue-router'

  import TemplateView from '@ateme/cathodic-ui/src/components/template/TemplateView.vue'
  import BaseTable from '@ateme/cathodic-ui/src/components/collections/BaseTable.vue'
  import { EIconEdit, EIconValidations } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
  import { EDataType } from '@ateme/cathodic-ui/src/interfaces/TableEnum.ts'
  import type { BaseButtonDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons.d.ts'
  import type { BaseTagDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/tags.d.ts'
  import BaseLoader from '@ateme/cathodic-ui/src/components/elements/BaseLoader.vue'
  import { IEntity } from '@ateme/cathodic-ui/src/interfaces/PageHeader'

  import { IUser } from '@ateme/login-service/src/interfaces/Interfaces'
  import userAccessMixins from '../../../abilities/access/userAccessComposable.ts'
  import roleAccessComposable from '../../../abilities/access/roleAccessComposable.ts'
  import { abilitiesReady } from '../../../abilities/abilitiesState'
  import { useUsersManagement } from '../composables/usersComposable'
  import { IRole } from '@interfaces/Interfaces'
  import { rolesStore } from '@store/allStoreDefinition.ts'
  import { usersStore } from '../../../components/users/store'
  import { children, usersLink } from '../router'
  import { DropdownButtonDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons'
  import { upperFirst } from '@ateme/cathodic-ui/src/utils/StringUtils.ts'

  // #####################################
  // INJECT
  // #####################################
  // -------------------
  // Router
  // -------------------
  const router = useRouter()

  // -------------------
  // i18n
  // -------------------
  const { t } = useTranslation()

  const { canViewUsers, canAddUsers, canEditUsers, canRemoveUsers } = userAccessMixins()
  const { canViewRoles } = roleAccessComposable()
  // -------------------
  // store
  // -------------------
  const storeRoles = rolesStore()
  const { fillRoles, setIsExpertMode } = storeRoles
  const { getAllRoles, getIsExpertMode } = storeToRefs(storeRoles)
  const storeUsers = usersStore()
  const { fillUsers, fillAdmin } = storeUsers
  const { getUsers, getAdmin } = storeToRefs(storeUsers)
  // -------------------
  // options
  // -------------------
  const langPath: string = 'users.main'
  /**
   * Key.
   */
  const admin: string = 'ADMIN'
  const superAdmin: string = 'SUPERADMIN'
  const refreshKey: string = 'Password refresh status'
  const idp_name: string = 'IdP Name'
  const roles: string = 'Roles'
  const componentName: string = 'list-users-view'
  const username: string = 'Username'
  const administrator: string = 'all'
  // -------------------
  // composable
  // -------------------
  const { getIdpFromIdpName } = useUsersManagement()

  // #####################################
  // DATA
  // #####################################
  const selected = ref<IUser[]>([])
  const selectedNumber = ref<number>(0)
  const interval = ref<number | undefined>(undefined)
  const defaultExpertModeValue = ref<boolean>(false)

  // #####################################
  // HOOK
  // #####################################
  onBeforeMount(async () => {
    await fillAdmin()
    if (canViewUsers) {
      await fillUsers()
    }
    // Setting default expert mode value to set it back on page exit
    defaultExpertModeValue.value = getIsExpertMode.value
    // Setting expert mode to true to display all roles correctly
    setIsExpertMode(true)
    if (canViewRoles) {
      await fillRoles()
    }

    if (!interval.value) interval.value = window.setInterval(() => fillUsers(), 10000)
  })

  onBeforeUnmount(() => {
    // Setting back expert mode value to its default value
    setIsExpertMode(defaultExpertModeValue.value)
    // clear interval when leaving page
    if (interval.value) {
      clearInterval(interval.value)
    }
  })
  // #####################################
  // COMPUTED
  // #####################################
  const columns = computed(() => {
    return [
      {
        name: username,
        path: 'username',
        sortable: true,
        defaultSort: true,
        resizable: true
      },
      {
        name: roles,
        path: 'roles',
        sortable: true,
        dataType: EDataType.Tag,
        resizable: true
      },
      { name: idp_name, path: 'idp_name', sortable: true, resizable: true },
      {
        name: refreshKey,
        path: 'first_login',
        dataType: EDataType.Boolean,
        sortable: true,
        resizable: true
      }
    ]
  })
  const addUserBtnAction = computed(() => {
    return {
      icon: EIconValidations.AddCircle,
      label: t('common.add'),
      title: t('common.addTitleM', { name: t('common.user') }),
      disabled: !canAddUsers,
      eventClick: () => addUser()
    }
  })

  /**
   * Header button for all bulk actions button (delete, ...)
   * @returns {DropdownButtonDef} - The dropdown button definition for bulk actions
   */
  const bulkActionsButton = computed((): DropdownButtonDef => {
    return {
      label: upperFirst(t('common.actions')),
      title: t('common.actions'),
      icon: EIconValidations.CheckBox,
      disabled: !isSelection.value,
      locked: !canRemoveUsers,
      itemList: [
        {
          icon: EIconEdit.Delete,
          name: t('common.delete'),
          disabled: !isSelection.value,
          locked: !canRemoveUsers,
          title: t('common.deleteSelectedTitleM', { name: t('common.users') }),
          eventClick: () => deleteSelected()
        }
      ]
    }
  })

  /**
   * Getter of time line entity.
   * @returns {object} - The Entity.
   */
  const entity = computed((): IEntity => {
    return usersLink
  })
  /**
   * Getter of eligible users
   * Test if users is OK.
   *@returns {object} - Users array.
   */
  const formattedUsers = computed((): IUser[] => {
    const formattedUsers: IUser[] = getUsers.value
    if (formattedUsers) {
      const usersWithId: IUser[] = cloneDeep(formattedUsers)
      return usersWithId.map((userWithId: IUser) => {
        return {
          ...userWithId,
          id: userWithId.user_id
        }
      })
    }
    return []
  })
  /**
   * Getter of admin
   *@returns {object} - Admin object.
   */
  const firstAdmin = computed((): IUser | undefined => {
    return getAdmin.value
  })
  /**
   * Test if a selection occurs
   * @returns {boolean} - <true> if selection exists , <false> else
   */
  const isSelection = computed((): boolean => {
    return !!selectedNumber.value
  })
  /**
   * Format displayed data for Role monitoring :
   * ex : ADMIN => Adminstrator
   *      OPERATOR => Operator except for SUPERADMIN
   * @returns {object} - The formatted data
   */
  const displayedUsers = computed((): IUser[] => {
    return map(formattedUsers.value, (user: IUser) => {
      const displayedUser = clone(user)
      if (displayedUser.roles[0] !== superAdmin) {
        if (displayedUser.roles[0] === admin) displayedUser.roles[0] = administrator
      }
      // Add a unicity key for the user to allow selection in the table
      displayedUser.user_unicity_key = `${displayedUser.username},${displayedUser.idp_name !== 'Local' ? displayedUser.idp_name : 'local'}`
      displayedUser.roles = formatRoles(user) as unknown as string[]
      displayedUser.idp_name = getIdpFromIdpName(user.idp_name as string)?.idp_label || user.idp_name
      displayedUser.first_login = user.first_login ? t(`${langPath}.view.pendingPasswordChange`) : ''
      return displayedUser
    })
  })

  // #####################################
  // METHODS
  // #####################################
  const actionButtons = (user: Partial<IUser>): BaseButtonDef[] => {
    const buttons: BaseButtonDef[] = []
    if (canRemoveUsers) {
      buttons.push({
        icon: EIconEdit.Delete,
        title: t('users.table.actions.delete', { name: user.username }),
        disabled: !canRemoveUsers || isAdmin(user.user_id as string),
        eventClick: () => deleteUser(user),
        id: `${componentName}-trash-${user.username}-${user.idp_name || 'local'}`
      } as BaseButtonDef)
    }
    if (canEditUsers) {
      buttons.push({
        icon: EIconEdit.Edit,
        title: t('users.table.actions.edit', { name: user.username }),
        disabled: !canEditUsers,
        eventClick: () => editUser(user),
        id: `${componentName}-pencil-${user.username}-${user.idp_name || 'local'}`
      } as BaseButtonDef)
    }
    return buttons
  }
  /**
   * Test if selected user is the Administrator
   * @param {string} user_id - the user id.
   * @returns {boolean} - <true> user is the administrator, <false> else.
   */
  const isAdmin = (user_id: string): boolean => {
    const admin: IUser | undefined = formattedUsers.value.find((user: IUser) => user.user_id === user_id)
    if (firstAdmin.value && admin) {
      return (
        admin &&
        admin.roles?.length === 1 &&
        admin.roles?.[0] === administrator &&
        admin.username === firstAdmin.value.username
      )
    }

    return false
  }
  /**
   * Get all roles by user object.
   * @param {object} user - user object.
   * @returns {string} - List of all roles.
   */
  const formatRoles = (user: IUser): BaseTagDef[] => {
    const allRoles = getAllRoles.value
    if (Array.isArray(user.roles) && user.roles.length === 1) {
      const findRole = allRoles.find((role: IRole) => role.id === user.roles?.[0])
      return findRole?.title ? [{ label: findRole.title }] : [{ label: t(`${langPath}.noFoundRole`) }]
    }

    return (user.roles as string[]).reduce((acc: BaseTagDef[], id: string): BaseTagDef[] => {
      if (id !== 'usr:guest') {
        const role: IRole | undefined = allRoles.find((role: IRole) => role.id === id)
        acc.push(
          role?.title ? { label: role.title as string } : { label: t(`${langPath}.noFoundRole`, { id }) as string }
        )
      }
      return acc
    }, [])
  }
  /**
   * Update route for multi deletion with an array of user names
   */
  const deleteSelected = () => {
    router.push(
      `${usersLink.path}/${children.delete}/${join(
        map(selected.value, user => `${user.idp_name}:${user.username}`),
        '~'
      )}`
    )
  }
  /**
   * The handler on selection
   * @param {object} newSelection - The user selected
   */
  const triggerSelect = (newSelection: string[]) => {
    const userToSelect: IUser[] = []
    newSelection.map((userId: string) => {
      const userSelected = getUsers.value.find((userItem: IUser) => {
        // Splitting the unicity key to get the username and idp_name
        return userItem.username === userId.split(',')[0] && userItem.idp_name === userId.split(',')[1]
      })
      if (userSelected) {
        userToSelect.push(userSelected)
      }
    })
    selected.value = userToSelect
    selectedNumber.value = selected.value.length
  }
  /**
   * Update route for adding a new user
   */
  const addUser = () => {
    pushRoute(children.add)
  }
  /**
   * Update route for mono deletion with a user name
   * @param {string} user - The user id to delete
   */
  const deleteUser = (user: Partial<IUser>) => {
    router.push(`${usersLink.path}/${children.delete}/${user.idp_name?.toLowerCase()}:${user.username}`)
  }
  /**
   * Update route for user name edition
   * @param {object} user - The user to edit
   */
  const editUser = (user: Partial<IUser>) => {
    pushRoute(`${children.edit}/${user.idp_name === 'Local' ? 'local' : user.idp_name}:${user.username}`)
  }
  /**
   * Update route
   * @param {string} route - The new route
   */
  const pushRoute = (route: string) => {
    router.push(`${usersLink.path}/${route}`)
  }
</script>

<template>
  <TemplateView
    v-if="canViewUsers || !abilitiesReady"
    data-testid="users-list-view"
    :entity="entity"
    class="list-users-view"
    :headerPrimaryAction="canAddUsers ? addUserBtnAction : undefined"
    :headerSecondaryAction="bulkActionsButton">
    <template #default>
      <BaseTable
        v-if="canViewUsers && displayedUsers"
        ref="users-base-table"
        data-testid="list-users-table"
        class="list-users-table"
        :data="displayedUsers"
        :columnList="columns"
        lineIdentifier="user_unicity_key"
        localStorageKey="USERS_TABLE"
        :hasPageFeature="true"
        :actionColumn="actionButtons"
        :onSelect="(user_unicity_key: string[]) => triggerSelect(user_unicity_key)" />
      <BaseLoader v-else />
    </template>
  </TemplateView>
</template>

<style lang="scss" scoped>
  .buttons {
    margin-bottom: 0.25rem;

    .base-button {
      margin-right: 1rem;
      width: 9rem;
    }
  }
  .list-users-table {
    max-height: 75vh;
  }
</style>
