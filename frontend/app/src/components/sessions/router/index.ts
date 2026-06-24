import { EIconSecurity } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
import { IEntity } from '@ateme/cathodic-ui/src/interfaces/PageHeader'
import { RouteLocationNormalized } from 'vue-router'

export const sessionsLink: IEntity = {
  path: '/sessions',
  name: 'Active sessions',
  icon: EIconSecurity.Logout,
  matchPath: [new RegExp(/^\/sessions.*$/)]
}

export const children = {
  delete: 'delete',
  update: 'update',
  edit: 'edit',
  editDetails: 'details'
}

export default [
  {
    path: sessionsLink.path,
    name: sessionsLink.name,
    meta: {
      userAccess: true
    },
    component: () => import(/* webpackChunkName: "user-management-sessions-list" */ '../views/ListView.vue'),
    children: [
      {
        path: `${children.delete}/:token_id`,
        name: `${sessionsLink.name}-${children.delete}`,
        meta: {
          userAccess: true,
          type: 'modal',
          props: {
            closable: false,
            closeOnMaskClick: true
          }
        },
        component: () => import(/* webpackChunkName: "user-management-sessions-delete" */ '../views/DeleteView.vue'),
        props: (route: RouteLocationNormalized) => ({
          token_id: route.params.token_id
        })
      }
    ]
  }
]
