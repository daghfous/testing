import { notificationStore } from '@ateme/cathodic-ui/src/components/notifications/notificationStore'
import { AxiosError, AxiosResponse } from 'axios'
import moment from 'moment'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useTranslation } from 'i18next-vue'
import { usersClient } from '@ateme/login-service/src/config/api'
import TokenService from '@ateme/login-service/src/services/TokenService'
import { IUnknownObjectKeys } from '@interfaces/Interfaces'

const { notifyError } = notificationStore()

/**
 * Process error cases of a request.
 * @param {object} resp - Response object.
 */
const errorInterceptor = async (resp: IUnknownObjectKeys) => {
  const { t } = useTranslation()
  const status = resp?.status || resp?.response?.status
  switch (status) {
    case 400:
      notifyError(t('users.errors.badRequest'), resp?.response?.data ?? resp?.message ?? '')
      return
    case 401:
      await TokenService.refreshTokenOrClearStorage()
      return
    case 404:
      notifyError(t('users.errors.notFound'), resp?.response?.data ?? resp?.message ?? '')
      return
    case status >= 500:
      notifyError(`${status} ${t('users.errors.serverError')}`, resp?.response?.data ?? resp?.message ?? '')
      return
  }
}

/**
 * User store {sessions}.
 * @returns {object} - Sessions Store
 */
export const sessionsStore = defineStore('sessions', () => {
  const { notifySuccess, notifyError } = notificationStore()
  // #####################################
  // STATE
  // #####################################
  const sessions = ref<IUnknownObjectKeys[]>([])

  // #####################################
  // GETTERS
  // #####################################
  const getSessions = computed((): IUnknownObjectKeys[] => sessions.value)

  // #####################################
  // ACTIONS
  // #####################################
  const setSessions = (newSessions: IUnknownObjectKeys[]) => {
    for (const session of newSessions) {
      session.started_date = moment.utc(session.started_date).local().format('DD/MM/YYYY HH:mm:ss')
      if (session.expiration_date !== 'unlimited') {
        session.expiration_date = moment.utc(session.expiration_date).local().format('DD/MM/YYYY HH:mm:ss')
      }
    }
    sessions.value = newSessions
  }
  /**
   * This method allow to view list of sessions.
   */
  const fillSessions = async () => {
    await usersClient
      .get('sessions', {
        headers: {
          'Content-Type': 'application/json',
          Authorization: TokenService.sessionToken
        }
      })
      .then((resp: AxiosResponse) => {
        if (resp.status === 200) {
          setSessions(resp.data)
        }
      })
      .catch((err: AxiosError) => {
        errorInterceptor(err)
      })
  }

  const deleteSession = async (token_id: string) => {
    await usersClient
      .delete(`sessions/${token_id}`, {
        headers: {
          'Content-Type': 'application/json',
          Authorization: TokenService.sessionToken
        }
      })
      .then((resp: AxiosResponse) => {
        if (resp.status === 200) {
          notifySuccess('Session deleted successfully')
          fillSessions()
        }
      })
      .catch((err: AxiosError) => {
        notifyError('Session deletion failed')
        errorInterceptor(err)
      })
  }

  return {
    getSessions,
    setSessions,
    fillSessions,
    deleteSession
  }
})
