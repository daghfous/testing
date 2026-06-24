import { EIconTravel } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
import { IEntity } from '@ateme/cathodic-ui/src/interfaces/PageHeader'
import { RouteLocationNormalized } from 'vue-router'

export const rolesLink: IEntity = {
  path: '/roles',
  name: 'Roles',
  icon: EIconTravel.Map,
  matchPath: [new RegExp(/^\/roles.*$/)]
}

/**
 * All children path.
 */
export const children = {
  add: 'add',
  duplicate: 'duplicate',
  delete: 'delete',
  edit: 'edit',
  listAvailableRoles: 'roles',
  addAvailableRoles: 'add',
  removeAvailableRole: 'remove',
  listAvailableActions: 'actions',
  addAvailableActions: 'add',
  removeAvailableAction: 'remove',
  editDetails: 'details'
}

export default [
  {
    path: rolesLink.path,
    name: rolesLink.name,
    component: () => import(/* webpackChunkName: "user-management-list-roles" */ '../views/ListView.vue'),
    children: [
      {
        path: `${children.delete}/:selectedRole`,
        name: `${rolesLink.name}-${children.delete}`,
        meta: {
          userAccess: true,
          type: 'modal',
          props: {
            closable: false,
            closeOnMaskClick: true
          }
        },
        component: () => import(/* webpackChunkName: "user-management-delete-roles" */ '../views/DeleteView.vue'),
        props: (route: RouteLocationNormalized) => ({
          selectedRoles: route.params.selectedRole
        })
      }
    ]
  },
  {
    path: `${rolesLink.path}/${children.add}`,
    name: `${rolesLink.name}-${children.add}`,
    component: () => import(/* webpackChunkName: "user-management-add-roles" */ '../views/AddDuplicateEditView.vue')
  },
  {
    path: `${rolesLink.path}/${children.duplicate}/:selectedRole`,
    name: `${rolesLink.name}-${children.duplicate}`,
    component: () =>
      import(/* webpackChunkName: "user-management-duplicate-roles" */ '../views/AddDuplicateEditView.vue'),
    props: (route: RouteLocationNormalized) => ({
      roleToDuplicate: route.params.selectedRole
    })
  },
  {
    path: `${rolesLink.path}/${children.edit}/:selectedRole`,
    name: `${rolesLink.name}-${children.edit}`,
    component: () => import(/* webpackChunkName: "user-management-add-roles" */ '../views/AddDuplicateEditView.vue'),
    props: (route: RouteLocationNormalized) => ({
      roleToEdit: route.params.selectedRole
    })
  }
]
