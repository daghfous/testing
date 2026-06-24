<script setup lang="ts">
  import { IColumn } from '@ateme/cathodic-ui/src/interfaces/Table.d'
  import type { BaseButtonDef } from '@ateme/cathodic-ui/src/interfaces/props/elements/buttons.d.ts'
  import { EIconEdit } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'

  import TemplateView from '@ateme/cathodic-ui/src/components/template/TemplateView.vue'
  import BaseTable from '@ateme/cathodic-ui/src/components/collections/BaseTable.vue'
  import { StoreGeneric, storeToRefs } from 'pinia'
  import { onBeforeMount, onBeforeUnmount, ref } from 'vue'
  import { useTranslation } from 'i18next-vue'
  import { useRouter } from 'vue-router'

  import { children, sessionsLink } from '../../../components/sessions/router'
  import { sessionsStore } from '../../../components/sessions/store'
  import { IUnknownObjectKeys } from '@interfaces/Interfaces.ts'
  import { loginServiceStore } from '@store/loginServiceStore.ts'
  import { usersLink } from '../../../components/users/router'
  import userAccessMixins from '../../../abilities/access/userAccessComposable.ts'

  // #####################################
  // INJECT
  // #####################################
  // -------------------
  // i18n
  // -------------------
  const { t } = useTranslation()

  const { canEditUsers, canUseForceUserDisconnection } = userAccessMixins()

  // -------------------
  // Router
  // -------------------
  const router = useRouter()

  // -------------------
  // store
  // -------------------
  const storeSessions = sessionsStore()
  const { getSessions } = storeToRefs(storeSessions)
  const { fillSessions } = storeSessions
  const { getIsAdmin } = storeToRefs(loginServiceStore() as StoreGeneric)

  // -------------------
  // options
  // -------------------
  const langPath: string = 'users.sessions'
  const componentName: string = 'sessions-list-view'
  // #####################################
  // DATA
  // #####################################
  const columns = ref<IColumn[]>([
    {
      name: t(`${langPath}.view.username`),
      path: 'username',
      sortable: true,
      defaultSort: true
    },
    {
      name: t(`${langPath}.view.idp_name`),
      path: 'idp_name',
      sortable: true,
      defaultSort: true
    },
    { name: t(`${langPath}.view.ip`), path: 'user_ip', sortable: true },
    {
      name: t(`${langPath}.view.started_date`),
      path: 'started_date',
      sortable: true
    },
    {
      name: t(`${langPath}.view.expiration_date`),
      path: 'expiration_date',
      sortable: true
    }
  ])
  const interval = ref<number | undefined>(undefined)

  // #####################################
  // HOOK
  // #####################################
  onBeforeMount(() => {
    fillSessions()
    if (!interval.value) interval.value = window.setInterval(() => fillSessions(), 10000)
  })

  onBeforeUnmount(() => {
    // clear interval when leaving page
    if (interval.value) {
      clearInterval(interval.value)
    }
  })
  // #####################################
  // METHODS
  // #####################################
  const actionButtons = (line: IUnknownObjectKeys): BaseButtonDef[] => {
    return [
      {
        icon: EIconEdit.Edit,
        title: t('users.table.actions.edit', { name: 'session' }),
        disabled: !canEditUsers,
        eventClick: () => editUser(line.user_id, line.username, line.idp_name),
        id: `${componentName}-pencil-${line.user_id}`
      } as BaseButtonDef,
      {
        icon: EIconEdit.Delete,
        title: t('users.table.actions.delete', { name: 'session' }),
        eventClick: () => deleteSession(line.token_id),
        id: `${componentName}-trash-${line.user_id}`
      } as BaseButtonDef
    ]
  }
  const deleteSession = (token_id: string) => {
    router.push(`${sessionsLink.path}/${children.delete}/${token_id}`)
  }

  const editUser = (user_id: string, username: string, idp_name: string) => {
    router.push(`${usersLink.path}/${children.edit}/${idp_name}:${username}`)
  }
</script>

<template>
  <TemplateView
    v-if="getIsAdmin || canUseForceUserDisconnection"
    data-testid="sessions-list-view"
    :entity="sessionsLink">
    <BaseTable
      v-if="getIsAdmin || canUseForceUserDisconnection"
      ref="sessionBaseTable"
      data-testid="users-sessions-base-table"
      class="list-sessions-table"
      :data="getSessions"
      :columnList="columns"
      :hasPageFeature="true"
      localStorageKey="SESSIONS_TABLE"
      :actionColumn="actionButtons" />
  </TemplateView>
</template>

<style lang="scss" scoped>
  .list-sessions-table {
    max-height: 75vh;
  }
</style>
