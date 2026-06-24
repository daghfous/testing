const AUTH_DATA: string[] = ['sessionToken', 'refreshToken', 'currentUserName']
const USER_DATA = [
  'currentUserName',
  'currentUserId',
  'currentUserIdpName',
  'isTokenActive',
  'firstLogin',
  'isAdmin',
  'preferences'
]
export default class AuthStorageService {
  /**
   * Write user data in the sessionStorage for retro-compatibility reason
   */
  static writeUserDataInSessionStorage() {
    USER_DATA.forEach((key: string) => {
      const value = this.getFromLocalStorage(key)
      if (value) {
        sessionStorage.setItem(key, value)
      }
    })
  }

  /**
   * Write authentication data in the sessionStorage for retro-compatibility reason
   */
  static writeAuthDataInSessionStorage() {
    AUTH_DATA.forEach((key: string) => {
      const value = this.getFromLocalStorage(key)
      if (value) {
        sessionStorage.setItem(key, value)
      }
    })
  }

  /**
   * Set the value in both session and local storages
   * @param {string} key Key of the item to set
   * @param {string} value Value of the item to set
   */
  static addToStorages(key: string, value: string | null) {
    this.addToLocalStorage(key, value)
    sessionStorage.setItem(key, value as string)
  }

  /**
   * Set the value in both session and local storages
   * @param {string} key Key of the item to set
   * @param {string} value Value of the item to set
   */
  static saveAuthToStorages(key: string, value: string | null) {
    this.addToLocalStorage(key, value)
    this.addToCookies(key, value)
    sessionStorage.setItem(key, value as string)
  }

  /**
   * Set the value in local storage
   * @param {string} key Key of the item to set
   * @param {string} value Value of the item to set
   */
  static addToLocalStorage(key: string, value: string | null) {
    const appId = process.env.APP_ID
    // When deploying an application in standalone mode, there is no releaseName
    if (appId) localStorage.setItem(`${appId}:${key}`, value as string)
    else localStorage.setItem(key, value as string)
  }

  /**
   * Get value from local storage
   * @param {string} key Key of the item to get
   * @returns {string} releaseName:key
   */
  static getFromLocalStorage(key: string) {
    const appId = process.env.APP_ID
    //If releaseName exists, returns the releaseName:key, otherwise return just key
    return appId ? localStorage.getItem(`${appId}:${key}`) : localStorage.getItem(key)
  }

  /**
   * Remove value from local storage
   * @param {string} key Key of the item to remove
   */
  static removeFromLocalStorage(key: string) {
    const appId = process.env.APP_ID
    if (appId) localStorage.removeItem(`${appId}:${key}`)
    else localStorage.removeItem(key)
  }

  /**
   * Add value to cookies
   * @param {string} key Key of the item to set
   * @param {string | null} value Value of the item to set
   * @param {number} [days] Number of days before the cookie expires
   */
  static addToCookies(key: string, value: string | null, days = 7) {
    const releaseName = location.pathname.split('/')[1]

    if (value === null) {
      document.cookie = `${key}=; path=/${releaseName}; expires=Thu, 01 Jan 1970 00:00:00 UTC;`
    } else {
      const d = new Date()
      d.setTime(d.getTime() + days * 24 * 60 * 60 * 1000)
      document.cookie = `${key}=${encodeURIComponent(value)}; path=/${releaseName}; expires=${d.toUTCString()}`
    }
  }

  /**
   * Get value from cookies
   * @param {string} key Key of the item to get
   * @returns {string | null} Value of the item or null if not found
   */
  static getFromCookies(key: string): string | undefined {
    const name = `${key}=`
    const match = decodeURIComponent(document.cookie)
      .split('; ')
      .find(row => row.includes(name))
    return match ? match.split(name)[1] : ''
  }
  /**
   * Delete cookies
   * @param {string[]} names - Cookies names to delete
   */
  static deleteCookies(names: string[]) {
    const pathNames = location.pathname.split('/')
    const pathsToDelete = [
      '/',
      `/${pathNames[1]}`,
      `/${pathNames[1]}/${pathNames[2]}`,
      `/${pathNames[1]}/`,
      `/${pathNames[1]}/${pathNames[2]}/`
    ]
    names.forEach((cookie: string) => {
      const [name] = cookie.trim().split('=')
      pathsToDelete.forEach(path => {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=${path};`
      })
    })
  }

  /**
   * Clear user and auth data from storages.
   * Do not simply empty storages as other informations can be stored there
   */
  static clearAuthAndUserDataFromStorages() {
    this.deleteCookies(AUTH_DATA)
    AUTH_DATA.concat(USER_DATA).forEach(key => {
      this.removeFromLocalStorage(key)
      sessionStorage.removeItem(key)
    })
  }
}
