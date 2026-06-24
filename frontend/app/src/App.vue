<script setup lang="ts">
  import RootPage from '@ateme/cathodic-ui/src/components/template/RootPage.vue'
  import { buildUserRights } from '@ateme/login-service/src/services/abilities/usersRights'
  import { useAbility } from '@casl/vue'
  import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
  import { useTranslation } from 'i18next-vue'
  import {
    NavigationGuardNext,
    onBeforeRouteLeave,
    onBeforeRouteUpdate,
    RouteLocationNormalized,
    useRouter
  } from 'vue-router'
  import { type StoreGeneric, storeToRefs } from 'pinia'
  import { CurrentRouteType, ILeftMenuItem } from '@ateme/cathodic-ui/src/interfaces/LeftMenu'
  import { IEntity } from '@ateme/cathodic-ui/src/interfaces/PageHeader'
  import DropdownButton from '@ateme/cathodic-ui/src/components/elements/DropdownButton.vue'
  import { IDropDownItem } from '@ateme/cathodic-ui/src/interfaces/DropDownLayout.d'
  import { EPopperPlacement } from '@ateme/cathodic-ui/src/interfaces/PopperEnum.ts'
  import { EIconSecurity } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
  import CurrentUserService from '@ateme/login-service/src/services/CurrentUserService'
  import { loginServiceStore } from '@store/loginServiceStore.ts'
  import { APP_VERSION, IS_DEPLOYED_WITH_PMF, VITE_TOP_MENU_STATIC_CONFIG } from './utils/constants.ts'
  import { usersLink } from './components/users/router'
  import { rolesLink } from './components/roles/router'
  import { idpLink } from './components/idp/router'
  import { sessionsLink } from './components/sessions/router'
  import { preferencesLink } from './components/preferences/router'
  import { isEmpty } from './utils/commonFunctions'

  import projectRight from './abilities/tree/rights'
  import projectTree from './abilities/tree/treeUpdate'
  import { projectRules } from './abilities/rules'
  import { abilitiesReady } from './abilities/abilitiesState'
  import useUserPermissions from './abilities/access/userAccessComposable'
  import useRolePermissions from './abilities/access/roleAccessComposable'
  import useIdPPermissions from './abilities/access/idpAccessComposable'

  // #####################################
  // INJECT
  // #####################################
  // -------------------
  // i18n
  // -------------------
  const { t } = useTranslation()
  const ability = useAbility()
  // -------------------
  // Router
  // -------------------
  const router = useRouter()
  // -------------------
  // store
  // -------------------
  const store = loginServiceStore()
  const { fillCurrentUserInfo, logout } = store
  const { getIsAdmin } = storeToRefs(store as StoreGeneric)
  // -------------------
  // permissions
  // -------------------
  const { canViewUsers, canUseForceUserDisconnection } = useUserPermissions()
  const { canViewRoles } = useRolePermissions()
  const { canViewIdP } = useIdPPermissions()
  // -------------------
  // options
  // -------------------
  const langPath: string = 'users.main'
  // #####################################
  // DATA
  // #####################################
  const interval = ref<number | undefined>(undefined)
  const currentRoute = ref<CurrentRouteType>({
    path: `/${router.currentRoute.value.path.split('/')[1]}`,
    query: router.currentRoute.value.query
  })
  const currentUserName = ref<string | null>('')
  // #####################################
  // HOOK
  // #####################################
  onMounted(async () => {
    await updateAbility()
    abilitiesReady.value = true
    await fillCurrentUserInfo()
    currentUserName.value = CurrentUserService.getUsername() || ''

    // Redirect if current route is not allowed after abilities are loaded
    const currentPath = router.currentRoute.value.path
    if (!isRouteAllowed(currentPath)) {
      router.replace(getDefaultRoute())
    }

    // Sync currentRoute after potential redirect
    currentRoute.value = {
      path: `/${router.currentRoute.value.path.split('/')[1]}`,
      query: router.currentRoute.value.query
    }

    // Guard future navigations
    router.beforeEach((to, _from, next) => {
      if (isRouteAllowed(to.path)) {
        next()
      } else {
        next(getDefaultRoute())
      }
    })

    if (!interval.value) interval.value = window.setInterval(() => fillCurrentUserInfo(), 10000)
  })

  onBeforeUnmount(() => {
    // clear interval when leaving page
    if (interval.value) {
      clearInterval(interval.value)
    }
  })
  // #####################################
  // ROUTER
  // #####################################

  onBeforeRouteUpdate((to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext) => {
    currentRoute.value = {
      path: `/${to.path.split('/')[1]}`,
      query: to.query
    }
    next()
  })
  onBeforeRouteLeave((to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext) => {
    // clear interval when leaving page
    if (interval.value) {
      clearInterval(interval.value)
    }
    next()
  })
  // #####################################
  // COMPUTED
  // #####################################

  /**
   * Path of the logo, changing if we are in pmf case or not
   */
  const logoPath = computed((): string => {
    return 'static-um/svg/USER_MANAGEMENT.svg'
  })
  /**
   * Get the tooltip of the Application manager logo
   * @returns {string} - the app manager tooltip
   */
  const tooltipText = computed((): string => {
    return t('users.versionTooltip', { version: APP_VERSION })
  })

  /**
   * All menus - items the user cannot access are shown greyed-out with a lock icon.
   * Before abilities are loaded, every item is shown unlocked to avoid a flash.
   */
  const allMenu = computed((): ILeftMenuItem[] => {
    const menuConfig: { entity: IEntity; allowed: boolean }[] = [
      { entity: usersLink, allowed: !abilitiesReady.value || canViewUsers.value },
      { entity: rolesLink, allowed: !abilitiesReady.value || canViewRoles.value },
      { entity: idpLink, allowed: !abilitiesReady.value || canViewIdP.value },
      {
        entity: sessionsLink,
        allowed: !abilitiesReady.value || canUseForceUserDisconnection.value || getIsAdmin.value
      },
      { entity: preferencesLink, allowed: !abilitiesReady.value || getIsAdmin.value }
    ]

    return menuConfig.map(
      ({ entity, allowed }): ILeftMenuItem =>
        ({
          path: entity.path.startsWith('/') ? entity.path : `/${entity.path}`,
          title: entity.name,
          icon: entity.icon,
          matchPath: entity.matchPath || undefined,
          disabled: false,
          locked: !allowed
        }) as ILeftMenuItem
    )
  })

  /**
   * Button of logout
   */
  const logoutButton = computed((): IDropDownItem[] => {
    return [
      {
        icon: EIconSecurity.Logout,
        name: t(`${langPath}.logOut`),
        eventClick: () => logout()
      }
    ]
  })
  // #####################################
  // METHODS
  // #####################################.
  /**
   * Updates the users abilities
   */
  const updateAbility = async () => {
    await buildUserRights({
      projectRight,
      projectTree,
      projectBuilders: projectRules,
      ability: ability
    })
  }

  /**
   * Checks whether a given route path is allowed for the current user
   * based on their CASL abilities.
   * @param {string} path - The route path to check.
   * @returns {boolean} `true` when the route is allowed.
   */
  const isRouteAllowed = (path: string): boolean => {
    // Own-profile route is always accessible for authenticated users
    if (path.includes('/users/update/me')) return true
    if (path.startsWith('/roles')) return canViewRoles.value
    if (path.startsWith('/idp')) return canViewIdP.value
    if (path.startsWith('/sessions')) return canUseForceUserDisconnection.value || getIsAdmin.value
    if (path.startsWith('/preferences')) return getIsAdmin.value
    if (path.startsWith('/users')) return canViewUsers.value
    return true
  }

  /**
   * Returns the first allowed route for the current user.
   * Falls back to the own-profile page when no section is accessible.
   * @returns {string} The path to redirect to.
   */
  const getDefaultRoute = (): string => {
    if (canViewUsers.value) return '/users'
    if (canViewRoles.value) return '/roles'
    if (canViewIdP.value) return '/idp'
    return '/users/update/me'
  }
</script>

<template>
  <div></div>
  <div class="user-management-app">
    <RootPage
      ref="userManagementSidebarLayout"
      :productLogo="logoPath"
      :allTabs="allMenu"
      logoId="sidebar-logo-user-management-home"
      :isSearchOption="false"
      :currentRoute="currentRoute"
      :isDemoVersion="false"
      :isPreviewVersion="false"
      :tooltipText="tooltipText"
      class="app"
      :class="{ 'pmf-app-height': IS_DEPLOYED_WITH_PMF }"
      pathOnClickLogo="users"
      :currentUserName="currentUserName"></RootPage>
    <DropdownButton
      v-if="!IS_DEPLOYED_WITH_PMF && (!VITE_TOP_MENU_STATIC_CONFIG || isEmpty(JSON.parse(VITE_TOP_MENU_STATIC_CONFIG)))"
      data-testid="connected-user"
      class="connected-user-button"
      :itemList="logoutButton"
      :popperContainerProps="{
        placement: EPopperPlacement.right
      }"
      :label="CurrentUserService.getUsername() || 'unknown'" />
  </div>
</template>

<style lang="scss">
  .product-logo {
    height: inherit;
  }
</style>
<style lang="scss" scoped>
  .connected-user-button {
    position: absolute;
    bottom: calc(var(--spacing-bigger-logo) + var(--spacing-double-base));
    left: var(--spacing-double-base);
    max-width: var(--sidebar-expanded-width);
  }
  .app {
    height: 100%;
  }
</style>
