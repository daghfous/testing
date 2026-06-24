import { EIconSettings } from '@ateme/cathodic-ui/src/interfaces/CathodicSvgIconEnum'

const PATH = 'preferences'
const NAME = 'Preferences'
export const preferencesLink = {
  path: PATH,
  name: NAME,
  icon: EIconSettings.Sliders1
}

export default {
  path: preferencesLink.path,
  name: preferencesLink.name,
  icon: preferencesLink.icon,
  component: () => import(/* webpackChunkName: "user-management-settings-view" */ '../views/SettingsView.vue')
}
