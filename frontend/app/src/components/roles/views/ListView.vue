<script setup lang="ts">
  import { IColumn } from '@ateme/cathodic-ui/src/interfaces/Table.d'
  import BaseLoader from '@ateme/cathodic-ui/src/components/elements/BaseLoader.vue'
  import TemplateView from '@ateme/cathodic-ui/src/components/template/TemplateView.vue'
  import { useAbility } from '@casl/vue'
  import join from 'lodash/join'
  import { computed, onBeforeMount, onBeforeUnmount, ref } from 'vue'
  import { useTranslation } from 'i18next-vue'
  import { useRouter } from 'vue-router'
  import { IEntity } from '@ateme/cathodic-ui/src/interfaces/PageHeader'
  import { debounce } from '@ateme/cathodic-ui/src/utils/debounce'

  import { useRoleManagement } from '../composables/rolesComposable'
  import { children, rolesLink } from '../router'
  import useRolePermissions from '../../../abilities/access/roleAccessComposable.ts'
  import { abilitiesReady } from '../../../abilities/abilitiesState'
  import { rolesStore } from '../../../components/roles/store'
  import { IRole } from '@interfaces/Interfaces'
  import BackendPaginatedTable from '@ateme/cathodic-ui/src/components/collections/BackendPaginatedTable.vue'
  import { storeToRefs } from 'pinia'
  import {
    EIconEdit,
    EIconNotesClipboard,
    EIconValidations
  } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum.ts'
  import type { BaseButtonDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons.d.ts'
  import { getRangeFromPaginatedQuery } from '@/utils/commonFunctions.ts'
  import { IPaginatedQuery } from '@ateme/cathodic-ui/src/interfaces/Table'
  import { DEFAULT_ROW_PER_PAGE_VALUES } from '../../../utils/constants.ts'
  import { DropdownButtonDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons'
  import { upperFirst } from '@ateme/cathodic-ui/src/utils/StringUtils.ts'
  // #####################################
  // INJECT
  // #####################################
  useAbility()
  // -------------------
  // Casl
  // -------------------
  const { canAddRoles, canEditRoles, canRemoveRoles, canViewRoles } = useRolePermissions()
  // -------------------
  // Store
  // -------------------
  const storeRoles = rolesStore()
  const { setCurrentRolesQuery, fillRoles, fillActions } = rolesStore()
  const { getPaginatedRoles, getNumberOfRoles, getCurrentRolesQuery, getMaxRolesRowPerPage } = storeToRefs(storeRoles)
  // -------------------
  // Router
  // -------------------
  const router = useRouter()
  // -------------------
  // i18n
  // -------------------
  const { t } = useTranslation()
  // -------------------
  // options
  // -------------------
  const langPath: string = 'users.roles'

  const componentName: string = 'ListRolesView'
  const { clickExpertMode, expertModeTitle, expertModeLabel, expertModeIcon } = useRoleManagement()
  // #####################################
  // DATA
  // #####################################
  const columns = ref<IColumn[]>([
    {
      name: t(`${langPath}.view.title`),
      path: 'title',
      resizable: true
    },
    {
      name: t(`${langPath}.view.label`),
      path: 'label',
      resizable: true
    },
    {
      name: t(`${langPath}.view.description`),
      path: 'description',
      resizable: true
    }
  ])
  const selected = ref<string[]>([])
  const selectedNumber = ref<number>(0)
  const interval = ref<number | undefined>(undefined)

  // #####################################
  // HOOK
  // #####################################
  onBeforeMount(async () => {
    debouncedFillRolesQuery()
    await fillActions()
    if (!interval.value) interval.value = window.setInterval(() => debouncedFillRolesQuery(), 10000)
  })

  onBeforeUnmount(() => {
    // clear interval when leaving page
    if (interval.value) {
      clearInterval(interval.value)
    }
  })
  // #####################################
  // COMPUTED
  // #####################################
  /**
   * Get the rowPerPage value from the store, with max value from the backend.
   * @returns {number[]} - The rowPerPage value.
   */
  const rolesCustomRowPerPage = computed((): number[] => {
    if (getMaxRolesRowPerPage.value !== undefined) {
      return DEFAULT_ROW_PER_PAGE_VALUES.filter((value: number) => value <= (getMaxRolesRowPerPage.value as number))
    } else return DEFAULT_ROW_PER_PAGE_VALUES
  })
  /**
   * Getter of time line entity.
   * @returns {object} - The Entity.
   */
  const entity = computed((): IEntity => {
    return rolesLink
  })
  /**
   * Getter of expert/basic mode button switch.
   * @returns {BaseButtonDef} - The button definition for the switch.
   */
  const expertBasicModeSwitchButton = computed((): BaseButtonDef => {
    return {
      label: expertModeLabel.value,
      icon: expertModeIcon.value,
      title: expertModeTitle.value,
      eventClick: async () => {
        clickExpertMode()
        // Have to call fill roles after setting mode to get the new total then get the paginated query
        debouncedFillRolesQuery()
      }
    }
  })
  /**
   * Test if a selection occurs
   * @returns {boolean} - <true> if selection exists , <false> else
   */
  const isSelection = computed((): boolean => {
    return !!selectedNumber.value
  })
  const addRoleBtnAction = computed(() => {
    return {
      icon: EIconValidations.AddCircle,
      label: t('common.add'),
      title: t('common.addTitleM', { name: 'role' }),
      id: 'add-roles-btn',
      disabled: !canAddRoles,
      eventClick: () => addRole()
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
      locked: !canRemoveRoles,
      itemList: [
        {
          icon: EIconEdit.Delete,
          name: t('common.delete'),
          disabled: !isSelection.value,
          locked: !canRemoveRoles,
          title: t('common.deleteSelectedTitleM', { name: 'roles' }),
          eventClick: () => deleteSelected()
        }
      ]
    }
  })

  // #####################################
  // METHODS
  // #####################################
  /**
   * Method to fetch paginated roles
   */
  const fetchRoles = async () => {
    await fillRoles({
      range: getRangeFromPaginatedQuery(getCurrentRolesQuery.value, getNumberOfRoles.value)
    })
  }

  /**
   * Debounce query for fetching roles
   */
  const debouncedFillRolesQuery = debounce(fetchRoles, 500)

  /**
   * Method called on query change of the roles table.
   * Set the currentQuery value and call debounceFillRolesQuery
   * @param {IPaginatedQuery} query - The query from the table
   */
  const onQueryChange = (query: IPaginatedQuery) => {
    setCurrentRolesQuery(query)
    debouncedFillRolesQuery()
  }

  /**
   * The buttons of the table rows
   * @param {IRole} role - The role to get action button from
   * @returns {BaseButtonDef[]} - The list of buttons
   */
  const actionButtons = (role: IRole): BaseButtonDef[] => {
    return [
      {
        icon: EIconNotesClipboard.CheckClipboard,
        title: t('users.table.actions.duplicate', { name: role.title }),
        disabled: !canAddRoles,
        eventClick: () => duplicateRole(role.id as string),
        id: `${componentName}-duplicate-${role.id}`
      } as BaseButtonDef,
      {
        icon: EIconEdit.Delete,
        title: t('users.table.actions.delete', { name: role.title }),
        disabled: !canRemoveRoles || isDefault(role),
        eventClick: () => deleteRole(role.id as string),
        id: `${componentName}-delete-${role.id}`
      } as BaseButtonDef,
      {
        icon: EIconEdit.Edit,
        title: t('users.table.actions.edit', { name: role.title }),
        disabled: !canEditRoles || isDefault(role),
        eventClick: () => editRole(role.id as string),
        id: `${componentName}-edit-${role.id}`
      } as BaseButtonDef
    ]
  }

  /**
   * Update route for adding a new role
   */
  const addRole = () => {
    pushRoute(children.add)
  }
  /**
   * Update route for duplicate a role
   * @param {string} role_id - the role id to duplicate
   */
  const duplicateRole = (role_id: string) => {
    pushRoute(`${children.duplicate}/${role_id}`)
  }
  /**
   * Update route for multi deletion with an array of role id
   */
  const deleteSelected = () => {
    pushRoute(`${children.delete}/${join(selected.value, '~')}`)
  }
  /**
   * The handler on selection
   * @param {Array<string>} ids - The role selected
   */
  const triggerSelect = (ids: string[]) => {
    selected.value = ids
    selectedNumber.value = ids.length
  }
  /**
   * Update route for mono deletion with a role id
   * @param {string} id - The role's id to delete
   */
  const deleteRole = (id: string) => {
    pushRoute(`${children.delete}/${id}`)
  }
  /**
   * Update route for role edition
   * @param {string} id - The role's id to edit
   */
  const editRole = (id: string) => {
    pushRoute(`${children.edit}/${id}`)
  }

  /**
   * Update route
   * @param {string} route - The new route
   */
  const pushRoute = (route: string) => {
    router.push(`${rolesLink.path}/${route}`)
  }
  /**
   * Check if the role is a default one.
   * @param {IRole} role - Role's id.
   * @returns {boolean} - return true if it's a default one, else return false.
   */
  const isDefault = (role: IRole): boolean => {
    return role ? !!role.default : false
  }
</script>

<template>
  <TemplateView
    v-if="canViewRoles"
    data-testid="roles-list-view"
    :entity="entity"
    class="roles-list-view"
    :headerPrimaryAction="addRoleBtnAction"
    :headerSecondaryAction="expertBasicModeSwitchButton"
    :headerOptionalAction="bulkActionsButton">
    <BackendPaginatedTable
      v-if="canViewRoles && getPaginatedRoles"
      ref="roles-base-table"
      data-testid="list-roles-table"
      class="list-roles-table"
      :data="getPaginatedRoles"
      :columnList="columns"
      lineIdentifier="id"
      localStorageKey="ROLES_TABLE"
      :hasPageFeature="true"
      :customItemsPerPageValues="rolesCustomRowPerPage"
      :nbTotalLine="getNumberOfRoles"
      :actionColumn="actionButtons"
      :onSelect="triggerSelect"
      :onQuery="onQueryChange" />
  </TemplateView>
  <BaseLoader v-else-if="!abilitiesReady" />
</template>

<style lang="scss" scoped>
  .buttons {
    margin-bottom: 0.25rem;

    .base-button {
      margin-right: 1rem;
      width: 9rem;
    }
  }
  .list-roles-table {
    max-height: 75vh;
  }
  .data-table {
    margin-top: 1rem;
  }
</style>
