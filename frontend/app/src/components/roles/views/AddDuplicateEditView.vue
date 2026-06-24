<script setup lang="ts">
  import { computed, onBeforeMount, ref } from 'vue'
  import { EIconSettings, EIconValidations } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
  import { IRole, IRoleAction, IUnknownObjectKeys } from '@interfaces/Interfaces.ts'
  import TemplateView from '@ateme/cathodic-ui/src/components/template/TemplateView.vue'
  import BaseLoader from '@ateme/cathodic-ui/src/components/elements/BaseLoader.vue'
  import BubbleText from '@ateme/cathodic-ui/src/components/elements/BubbleText.vue'
  import type { BreadCrumbsDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/breadCrumbs.d.ts'
  import { IEntity } from '@ateme/cathodic-ui/src/interfaces/PageHeader'
  import { rolesLink } from '../router/index'
  import { rolesStore } from '../../../components/roles/store'
  import { useTranslation } from 'i18next-vue'
  import { useRouter } from 'vue-router'
  import { storeToRefs } from 'pinia'
  import SeparatorHeader from '@ateme/cathodic-ui/src/components/elements/SeparatorHeader.vue'
  import snakeCase from 'lodash/snakeCase'
  import BaseCard from '@ateme/cathodic-ui/src/components/containers/BaseCard.vue'
  import TextInput from '@ateme/cathodic-ui/src/components/inputs/TextInput.vue'
  import cloneDeep from 'lodash/cloneDeep'
  import type { BaseButtonDef, PromiseButtonDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons.d.ts'
  import RolesBaseCard from '../../../components/common/RolesBaseCard.vue'
  import ActionsBaseCard from '../../../components/common/ActionsBaseCard.vue'
  import RouteConfirm from '../../common/RouteConfirm.vue'
  import { EBubbleTextType } from '@ateme/cathodic-ui/src/interfaces/BubbleTextEnum.ts'
  import { EIconOtherDevice } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum.ts'
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
  const storeRoles = rolesStore()
  const { fillRoles, createRole, edit, fillActions } = storeRoles
  const { getAllRoles, getActions, getNumberOfRoles } = storeToRefs(storeRoles)
  // -------------------
  // options
  // -------------------
  const langPath: string = 'users.roles'

  // #####################################
  // PROPS / EVENTS
  // #####################################
  export type rolesViewsAddProps = {
    /**
     * Selected user for edit.
     */
    roleToDuplicate?: string
    roleToEdit?: string
  }

  const props = withDefaults(defineProps<rolesViewsAddProps>(), {
    roleToDuplicate: undefined,
    roleToEdit: undefined
  })

  // #####################################
  // HOOK
  // #####################################
  onBeforeMount(async () => {
    if (!getNumberOfRoles.value || props.roleToDuplicate || props.roleToEdit) {
      await fillRoles()
    }
    await fillActions()
    initData()
    isLoading.value = false
  })
  // #####################################
  // DATA
  // #####################################
  const entity = ref<IEntity>(rolesLink)
  const editMode = ref<boolean>(!!props.roleToEdit)
  const roleModel = ref<IRole>({})
  const error = ref<string>('')
  const currentRole = ref<IRole>({})
  const submitted = ref<boolean>(false)
  const currentRoles = ref<IRole[]>([])
  const currentActions = ref<IRoleAction[]>([])
  const submitButtonLabels: [string, string, string, string] = [
    t('common.save'),
    t('common.saving'),
    t('common.saved'),
    t('common.cantSave')
  ]
  // Wait for data before displaying it
  const isLoading = ref<boolean>(true)

  /**
   * @description Button to cancel the role edition/creation, make the user returns to the roles list view
   */
  const cancelButton: BaseButtonDef = {
    icon: EIconValidations.ClearCircle,
    label: t('common.cancel'),
    title: t('common.cancel'),
    eventClick: () => router.push(rolesLink.path)
  }
  // #####################################
  // COMPUTED
  // #####################################
  /**
   * Test if there is a error.
   * @returns {boolean} - <true> there is a error, <false> else.
   */
  const hasError = computed((): boolean => {
    return !isValidDuplication()
  })

  const submitButton = computed((): PromiseButtonDef => {
    return {
      disabled: hasError.value || !hasChanged(),
      labels: submitButtonLabels,
      icon: EIconOtherDevice.Save,
      title: t('common.save'),
      handler: async () => await validateAndSubmit()
    }
  })
  const breadCrumbs = computed((): BreadCrumbsDef => {
    const elementList = [
      entity.value.name,
      props.roleToEdit
        ? t('common.editWithName', { name: props.roleToEdit })
        : props.roleToDuplicate
          ? t('common.duplicateWithName', { name: props.roleToDuplicate })
          : t(`${langPath}.headerLabel`)
    ]
    return {
      id: 'add-duplicate-edit-role',
      elementList: elementList,
      routerPushHandler: event => {
        // Can only click on deployed apps
        if (event.length === 1) {
          router.push(rolesLink.path)
        }
      }
    } as BreadCrumbsDef
  })

  // #####################################
  // METHODS
  // #####################################
  /**
   * Initialization of all current data.
   */
  const initData = () => {
    if (props.roleToDuplicate || props.roleToEdit) {
      currentRole.value = cloneDeep(
        getAllRoles.value.filter((item: IRole) => {
          return props.roleToDuplicate ? item.id === props.roleToDuplicate : item.id === props.roleToEdit
        })[0]
      )

      roleModel.value = { ...currentRole.value }
      currentRoles.value = getAllRoles.value.filter((role: IRole) => {
        return currentRole.value.content?.some((item: IRoleAction) => item.scope === role.id) ?? false
      })
      currentActions.value = getActions.value.filter((action: IRoleAction) => {
        return currentRole.value.content?.some((item: IRoleAction) => item.action === action.action) ?? false
      })
      if (props.roleToDuplicate) {
        delete currentRole.value.id
        isValidDuplication()
      }
    }
  }

  /**
   * Check if the duplication is valid
   * @returns {boolean} - <true> if valid, <false> else.
   */
  const isValidDuplication = (): boolean => {
    error.value = ''
    if (!props.roleToEdit) {
      if (!currentRole.value.title || !currentRole.value.label || !currentRole.value.description) {
        error.value = 'All inputs must be filled'
        return false
      }
      if (props.roleToDuplicate && currentRole.value.title === roleModel.value.title) {
        error.value = 'Input title equals initial title'
        return false
      }

      const allRoles = getAllRoles.value.map((item: IRole) => item.title)
      if (allRoles.includes(currentRole.value.title)) {
        error.value = 'Input title already exists'
        return false
      }
    }
    return true
  }

  /**
   * Event of submit.
   */
  const validateAndSubmit = async () => {
    submitted.value = true

    const rolesAndActionsToSend: IUnknownObjectKeys[] = currentRoles.value.map(r => {
      return { scope: r.id }
    })
    currentActions.value.map((a: IUnknownObjectKeys) => {
      rolesAndActionsToSend.push(a)
    })
    const roleToSend: IRole = {
      label: currentRole.value.label,
      title: currentRole.value.title,
      id: props.roleToEdit ? props.roleToEdit : 'custom:' + snakeCase(currentRole.value.title),
      description: currentRole.value.description,
      content: rolesAndActionsToSend as IRoleAction[]
    }
    if (props.roleToEdit) {
      await edit(roleToSend)
        .then(async () => {
          await fillRoles()
          router.push(rolesLink.path)
        })
        .catch(err => {
          error.value = err
        })
    } else {
      await createRole(roleToSend)
        .then(async () => {
          await fillRoles()
          router.push(rolesLink.path)
        })
        .catch(err => {
          error.value = err
        })
    }
  }
  type AvailableRolesResult = {
    roles: IRole[]
    totalFiltered: number
  }

  /**
   * Roles available for selection + filtered total count.
   * totalFiltered uses backend total (Content-Range) when available.
   * @returns {AvailableRolesResult} - The roles and total filtered
   */
  const availableRolesData = computed((): AvailableRolesResult => {
    const selectedRoleIds = new Set(currentRoles.value.map(r => r.id as string))
    const roles = (getAllRoles.value ?? []).filter((role: IRole) => {
      return !selectedRoleIds.has(role.id as string)
    })

    // Get total from backend and substract already added roles
    const backendTotal = getNumberOfRoles.value ?? getAllRoles.value.length
    const totalFiltered = Math.max(backendTotal - selectedRoleIds.size, 0)

    return { roles, totalFiltered }
  })

  /**
   * get the filtered roles
   * @returns {number} - The available roles
   */
  const availableRolesList = computed((): IRole[] => availableRolesData.value.roles)

  /**
   * get the filtered total number of roles
   * @returns {number} - The available roles length
   */
  const availableRolesTotalFiltered = computed((): number => availableRolesData.value.totalFiltered)

  /**
   * The available roles list
   * @returns {Array} - list of roles
   */
  const availableActionsList = computed((): IRole[] => {
    let listsActions: IRole[] = []
    if (!currentRole.value && !currentActions.value) {
      return listsActions
    }
    listsActions = getActions.value?.filter((action: IRoleAction) => {
      const roleActions = currentActions.value.map(a => a.action)
      return !roleActions.includes(action.action as string)
    })

    return listsActions
  })
  const handleRolesUpdate = (roles: IRole[]) => {
    currentRoles.value = roles
    const rolesAndActionsToSend: IUnknownObjectKeys[] = currentRoles.value.map(r => {
      return { scope: r.id }
    })
    currentActions.value.map((a: IUnknownObjectKeys) => {
      rolesAndActionsToSend.push(a)
    })
    currentRole.value.content = rolesAndActionsToSend
  }
  const handleActionsUpdate = (actions: IRoleAction[]) => {
    currentActions.value = actions
    const rolesAndActionsToSend: IUnknownObjectKeys[] = currentRoles.value.map(r => {
      return { scope: r.id }
    })
    currentActions.value.map((a: IUnknownObjectKeys) => {
      rolesAndActionsToSend.push(a)
    })
    currentRole.value.content = rolesAndActionsToSend
  }

  const hasChanged = (): boolean => {
    return JSON.stringify(currentRole.value) !== JSON.stringify(roleModel.value) && !submitted.value
  }
</script>

<template>
  <TemplateView
    data-testid="add-edit-duplicate-role-view"
    :entity="entity"
    :headerPrimaryAction="submitButton"
    :headerSecondaryAction="cancelButton"
    :breadCrumbsProps="breadCrumbs">
    <RouteConfirm :hasPendingChanges="hasChanged()"></RouteConfirm>
    <div
      v-if="!isLoading"
      class="base-cards">
      <BaseCard
        data-testid="role-form-card"
        :name="t('users.main.general')">
        <BubbleText
          v-if="error"
          data-testid="error-message"
          :type="EBubbleTextType.Danger"
          :label="error" />
        <form
          class="role-form"
          @keyup.enter="validateAndSubmit">
          <TextInput
            v-model="currentRole.title"
            data-testid="role-title"
            :title="t(`${langPath}.textTitle`)"
            required />
          <TextInput
            v-model="currentRole.label"
            data-testid="role-label"
            :title="t(`${langPath}.labelTitle`)"
            required />
          <TextInput
            v-model="currentRole.description"
            data-testid="role-description"
            :title="t(`${langPath}.descriptionTitle`)"
            required />
        </form>
      </BaseCard>
      <RolesBaseCard
        :availableRolesList="availableRolesList"
        :availableRolesTotalFiltered="availableRolesTotalFiltered"
        :editMode="editMode"
        :currentRolesIds="currentRoles.map(role => role.id as string)"
        @update:currentRoles="handleRolesUpdate" />
      <SeparatorHeader
        data-testid="actions"
        :name="t(`${langPath}.addOtherActions`)"
        :collapseValue="false"
        :icon="EIconSettings.Settings2">
        <ActionsBaseCard
          :availableActionsList="availableActionsList"
          :editMode="editMode"
          :currentActions="currentActions"
          @update:currentActions="handleActionsUpdate" />
      </SeparatorHeader>
    </div>
    <BaseLoader v-else />
  </TemplateView>
</template>

<style scoped lang="scss">
  .role-form {
    margin-top: var(--spacing-base);
    display: flex;
    gap: 16px; /* Adjust spacing between fields */
    align-items: center; /* Align items vertically */
  }
  .base-cards {
    display: flex;
    flex-direction: column;
    gap: 16px; /* Adjust padding as needed */
  }
</style>
