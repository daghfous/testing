import { EIconUser } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'
import { IEntity } from '@ateme/cathodic-ui/src/interfaces/PageHeader'
import { RouteLocationNormalized } from 'vue-router'

const PATH: string = '/idp'
const NAME: string = 'IdPs'

export const idpLink: IEntity = {
  path: PATH,
  name: NAME,
  icon: EIconUser.UserGroup,
  matchPath: [new RegExp(/^\/idp.*$/)]
}

/**
 * All children path.
 */
export const children = {
  add: 'add',
  edit: 'edit',
  delete: 'delete',
  details: 'details',
  roleMapping: 'roleMapping',
  addMapper: 'addMapper',
  editMapper: 'editMapper',
  removeMapper: 'removeMapper'
}

export default [
  {
    path: idpLink.path,
    name: idpLink.name,
    component: () => import(/* webpackChunkName: "user-management-list-idp" */ '../views/ListView.vue'),
    children: [
      {
        path: `${children.delete}/:idpName`,
        name: `${idpLink.name}-${children.delete}`,
        meta: {
          userAccess: true,
          type: 'modal',
          props: {
            closable: false,
            closeOnMaskClick: true
          }
        },
        component: () => import(/* webpackChunkName: "user-management-delete-idp" */ '../views/DeleteView.vue'),
        props: (route: RouteLocationNormalized) => ({
          idpName: route.params.idpName
        })
      }
    ]
  },
  {
    path: `${idpLink.path}/${children.add}`,
    name: `${idpLink.name}-${children.add}`,
    component: () => import(/* webpackChunkName: "user-management-add-idp" */ '../views/AddEditView.vue')
  },
  {
    path: `${idpLink.path}/${children.edit}/:idpName`,
    name: `${idpLink.name}-${children.edit}`,
    meta: {
      userAccess: true,
      type: 'modal'
    },
    component: () => import(/* webpackChunkName: "user-management-edit-idp" */ '../views/AddEditView.vue'),
    props: (route: RouteLocationNormalized) => ({
      idpName: route.params.idpName
    })
  }
]
