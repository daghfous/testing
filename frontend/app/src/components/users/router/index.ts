import { RouteLocationNormalized } from 'vue-router'
import { IEntity } from '@ateme/cathodic-ui/src/interfaces/PageHeader'
import { EIconUser } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'

/**
 * Link is used to be displayed (somewhere) and to navigate over the route.
 */
export const usersLink: IEntity = {
  path: '/users',
  name: 'Users',
  icon: EIconUser.User1,
  matchPath: [new RegExp(/^\/users.*$/)]
}

/**
 * All children path.
 */
export const children = {
  add: 'add',
  edit: 'edit',
  update: 'update',
  delete: 'delete',
  addUserRoles: 'add',
  listUserRoles: 'roles',
  removeUserRole: 'remove'
}

export default [
  {
    path: usersLink.path,
    name: usersLink.name,
    component: () => import(/* webpackChunkName: "user-management-list-users" */ '../views/ListView.vue'),
    children: [
      // Remove a user
      {
        path: `${children.delete}/:selectedUser`,
        name: `${usersLink.name}-${children.delete}`,
        meta: {
          userAccess: true,
          type: 'modal',
          props: {
            closable: false,
            closeOnMaskClick: true
          }
        },
        component: () => import(/* webpackChunkName: "user-management-list-roles" */ '../views/DeleteView.vue'),
        props: (route: RouteLocationNormalized) => ({
          selectedUsers: route.params.selectedUser
        })
      }
    ]
  },
  // Add a user
  {
    path: `${usersLink.path}/${children.add}`,
    name: `${usersLink.name}-${children.add}`,
    component: () => import(/* webpackChunkName: "user-management-add-users" */ '../views/AddEditView.vue')
  },
  // Edit a user
  {
    path: `${usersLink.path}/${children.edit}/:selectedUser`,
    name: `${usersLink.name}-${children.edit}`,
    component: () => import(/* webpackChunkName: "user-management-users-edit-details" */ '../views/AddEditView.vue'),
    props: (route: RouteLocationNormalized) => ({
      initialUser: route.params.selectedUser
    })
  },
  // Deprecated edit /me route (for portal not to break)
  {
    path: `${usersLink.path}/${children.update}/me`,
    name: `${usersLink.name}-${children.edit}-me`,
    component: () => import(/* webpackChunkName: "user-management-users-edit-my-details" */ '../views/AddEditView.vue')
  }
]
