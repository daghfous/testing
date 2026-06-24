import { debounce } from '@ateme/cathodic-ui/src/utils/debounce'
import { TrackUserActionsOptions } from '../interfaces/Interfaces.ts'

const DEBOUNCE_TIMEOUT = 1000 // 1000ms = 1 seconde
const WINDOW_EVENTS_TO_TRACK = ['mousemove', 'scroll', 'keydown', 'resize']
const INACTIVE_USER_TIME_THRESHOLD = 3600000
class ActivityService {
  private userActivityTimeout?: number
  private timeout: number | null
  private _isActive: boolean
  private debouncedFunction: () => void
  private timeoutAction: (() => void) | null

  constructor() {
    this.userActivityTimeout = undefined
    this.timeout = null
    this._isActive = true
    this.debouncedFunction = () => {}
    this.timeoutAction = () => {}
  }

  /**
   * Reset user activity
   * @static
   */
  resetUserActivity() {
    this._isActive = true
    clearTimeout(this.userActivityTimeout as number)
    this.userActivityTimeout = setTimeout(() => {
      this.inactiveUser()
    }, this.timeout as number) as unknown as number
  }

  /**
   * @description Set user as inactive
   * @static
   */
  inactiveUser() {
    this._isActive = false
    if (this.timeoutAction) this.timeoutAction()
  }

  /**
   * @description Track window user actions
   * @param {object} options -  options for service
   */
  trackUserActions(options: TrackUserActionsOptions = {}): void {
    const {
      inactivityTimeout = INACTIVE_USER_TIME_THRESHOLD,
      debounceTimeout = DEBOUNCE_TIMEOUT,
      inactiveUserAction = null
    } = options

    this.timeout = inactivityTimeout
    this.debouncedFunction = debounce(this.resetUserActivity.bind(this), debounceTimeout) as () => void
    this.timeoutAction = inactiveUserAction || null

    WINDOW_EVENTS_TO_TRACK.forEach(key => {
      window.addEventListener(key as keyof WindowEventMap, this.debouncedFunction)
    })

    // FE-1437 Launch inactivity timeout once tracking parameters have been set
    this.debouncedFunction()
  }
  /**
   * @description Return if user is active or not
   * @static
   * @returns {boolean} true if user is active, false otherwise
   */
  isActive(): boolean {
    return this._isActive
  }

  /**
   * @description Remove tracked user event on window
   * @static
   */
  removeTrackUserActions() {
    WINDOW_EVENTS_TO_TRACK.forEach((key: string) => {
      window.removeEventListener(key as keyof WindowEventMap, this.debouncedFunction as () => void)
    })

    clearTimeout(this.userActivityTimeout as number)
  }
}
const activityService: ActivityService = new ActivityService()
export default activityService
