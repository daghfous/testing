/**
 * Custom element interface for the app switcher component.
 */
export interface IUserConfigElement {
  userName: string
  onEditProfile: () => void
  onLogout: () => void
}

export interface IUserProfileElement extends HTMLElement {
  userConfig: IUserConfigElement,
  activeSection: string,
  appendTo?: Element | HTMLElement
}

