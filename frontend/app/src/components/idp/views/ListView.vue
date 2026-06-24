<script setup lang="ts">
  import { IColumn } from '@ateme/cathodic-ui/src/interfaces/Table.d'
  import BaseLoader from '@ateme/cathodic-ui/src/components/elements/BaseLoader.vue'
  import TemplateView from '@ateme/cathodic-ui/src/components/template/TemplateView.vue'
  import { storeToRefs } from 'pinia'
  import { computed, onBeforeMount, onBeforeUnmount, ref } from 'vue'
  import { useTranslation } from 'i18next-vue'
  import { useRouter } from 'vue-router'
  import { EIconEdit, EIconValidations } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
  import BaseTable from '@ateme/cathodic-ui/src/components/collections/BaseTable.vue'
  import { IEntity } from '@ateme/cathodic-ui/src/interfaces/PageHeader'
  import type { BaseButtonDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons.d.ts'

  import { children, idpLink } from '../router/index'
  import useIdPPermissions from '../../../abilities/access/idpAccessComposable.ts'
  import { abilitiesReady } from '../../../abilities/abilitiesState'
  import { IIdp } from '@interfaces/Interfaces.ts'
  import { idpStore } from '@store/allStoreDefinition.ts'

  // #####################################
  // INJECT
  // #####################################
  // -------------------
  // i18n
  // -------------------
  const { t } = useTranslation()
  // -------------------
  // Casl
  // -------------------
  const { canViewIdP, canAddIdP, canEditIdP, canRemoveIdP } = useIdPPermissions()
  // -------------------
  // Router
  // -------------------
  const router = useRouter()
  // -------------------
  // store
  // -------------------
  const storeIdp = idpStore()
  const { fillIdPs } = storeIdp
  const { getIdPs } = storeToRefs(storeIdp)
  // -------------------
  // options
  // -------------------
  const componentName: string = 'IdPsList'
  const langPath: string = 'users.idp.columns'
  // #####################################
  // DATA
  // #####################################
  const columns = ref<IColumn[]>([
    { name: t(`${langPath}.type`), path: 'idp_type', sortable: true },
    {
      name: t(`${langPath}.name`),
      path: 'idp_name',
      sortable: true,
      defaultSort: true
    },
    { name: t(`${langPath}.label`), path: 'idp_label', sortable: true }
  ])
  const entity = ref<IEntity>(idpLink)
  const interval = ref<number | undefined>(undefined)

  // #####################################
  // HOOK
  // #####################################
  onBeforeMount(async () => {
    await fillIdPs()
    if (!interval.value) interval.value = window.setInterval(() => fillIdPs(), 10000)
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

  const addIdPBtnAction = computed(() => {
    return {
      icon: EIconValidations.AddCircle,
      label: t('common.add'),
      title: t('common.addTitleM', { name: t('common.idp') }),
      disabled: !canAddIdP,
      eventClick: () => addIdP()
    }
  })
  /**
   * Format displayed data
   * @returns {object} - The formatted data
   */
  const displayedIdPs = computed((): IIdp[] => {
    return getIdPs.value
      .filter((idp: IIdp) => idp.idp_type !== 'local')
      .map((idp: IIdp) => {
        return {
          ...idp,
          idp_type: idp.idp_type?.toUpperCase()
        }
      })
  })

  // #####################################
  // METHODS
  // #####################################

  const actionButtons = (idp: IIdp): BaseButtonDef[] => {
    return [
      {
        icon: EIconEdit.Delete,
        title: t('users.table.actions.delete', { name: idp.idp_name }),
        disabled: !canRemoveIdP,
        eventClick: () => deleteIdP(idp.idp_name as string),
        id: `${componentName}-trash-${idp.idp_name}`
      } as BaseButtonDef,
      {
        icon: EIconEdit.Edit,
        title: t('users.table.actions.edit', { name: idp.idp_name }),
        disabled: !canEditIdP,
        eventClick: () => editIdP(idp.idp_name as string),
        id: `${componentName}-pencil-${idp.idp_name}`
      } as BaseButtonDef
    ]
  }
  /**
   * Update route for adding a new idp config
   */
  const addIdP = () => {
    pushRoute(children.add)
  }
  /**
   * Update route for mono deletion with a domain
   * @param {string} idp_name - The domain to delete
   */
  const deleteIdP = (idp_name: string) => {
    pushRoute(`${children.delete}/${idp_name}`)
  }
  /**
   * Update route for idp domain edition
   * @param {string} idp_name - The domain to edit
   */
  const editIdP = (idp_name: string) => {
    pushRoute(`${children.edit}/${idp_name}`)
  }
  /**
   * Update route
   * @param {string} route - The new route
   */
  const pushRoute = (route: string) => {
    router.push(`${idpLink.path}/${route}`)
  }
</script>

<template>
  <template-view
    v-if="canViewIdP"
    data-testid="list-idp-view"
    :entity="entity"
    class="list-idp-view"
    :headerPrimaryAction="addIdPBtnAction">
    <BaseTable
      v-if="canViewIdP"
      data-testid="idps-base-table"
      class="list-idps-table"
      hasPageFeature
      localStorageKey="IDPS_TABLE"
      lineIdentifier="idp_name"
      :data="displayedIdPs"
      :actionColumn="actionButtons"
      :columnList="columns" />
  </template-view>
  <base-loader v-else-if="!abilitiesReady" />
</template>

<style lang="scss" scoped>
  .list-idps-table {
    max-height: 75vh;
  }
</style>
