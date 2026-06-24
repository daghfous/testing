import { defineStore } from 'pinia'

import { usersClient } from '../../config/api'

export interface IAuthenticateModeState {
  authenticateMode: IAuthenticateMode[]
}

export interface IAuthenticateMode {
  name?: string | null
  idp_name?: string | null
  idp_label?: string | null
  idp_type?: string | null
  domain?: string[] | null
}

/**
 * User store {authenticateMode}.
 * @returns {object} - Authenticate Mode Store
 */
export const authenticateModeStore = defineStore('authenticateMode', {
  state: (): IAuthenticateModeState => ({
    authenticateMode: []
  }),

  getters: {
    /**
     * @param {object} state - the state.
     * @returns {Array} - authenticateMode.
     */
    getAuthenticateMode: (state: IAuthenticateModeState): IAuthenticateMode[] => state.authenticateMode
  },

  actions: {
    /**
     * @param {IAuthenticateMode[]} authenticateMode - the authenticate modes.
     */
    setAuthenticateMode(authenticateMode: IAuthenticateMode[]) {
      this.authenticateMode = authenticateMode
    },

    /**
     * Get all authenticate modes.
     * @returns {Promise<IAuthenticateMode[]>} - authenticate modes.
     */
    async getAuthenticateModes(): Promise<IAuthenticateMode[]> {
      const resp = await usersClient.get('authenticate_mode')
      if (resp.status === 200) {
        this.setAuthenticateMode(resp.data)
      }
      return resp?.data
    }
  }
})
