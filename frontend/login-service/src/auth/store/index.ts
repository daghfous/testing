import { defineStore } from 'pinia'

export interface IAuthStore {
  projectInitialize: unknown
}

export const authStore = defineStore('auth', {
  state: (): IAuthStore => ({
    projectInitialize: null as unknown
  }),
  getters: {
    getProjectInitialize(): unknown {
      return this.projectInitialize
    }
  },
  actions: {
    setProjectInitialize(value: unknown) {
      this.projectInitialize = value
    }
  }
})
