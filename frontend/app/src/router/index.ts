import { Router } from 'vue-router'
import createCathodicRouter, { ICreateRouter } from '@ateme/cathodic-ui/src/services/Router'

import idp from '../components/idp/router'
import roles from '../components/roles/router'
import sessions from '../components/sessions/router'
import preferences from '../components/preferences/router'
import users from '../components/users/router'
import App from '../App.vue'

import settingsViewsRouter from '@ateme/cathodic-ui/src/views/settingsPages/router/settingsViewsRouter'

const options = (projectName: string): ICreateRouter => {
  return {
    projectName,
    rootComponent: {
      component: App,
      children: [...users, ...roles, ...idp, ...sessions, preferences, settingsViewsRouter({ hideGeneral: true })]
    },
    defaultRedirectPath: '/users'
  }
}

export default (projectName: string): Router => createCathodicRouter({ ...options(projectName) })
