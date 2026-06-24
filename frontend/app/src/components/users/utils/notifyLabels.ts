import { INotifyLabel } from '@interfaces/Interfaces'

/**
 * Getter of create action Labels.
 * @param {string} username - user name.
 * @returns {object} - {pending, resolved, rejected}.
 */
const creatingLabel = (username: string): INotifyLabel => {
  return {
    pending: `Creating "${username}"`,
    resolved: `"${username}" successfully created!`,
    rejected: `Couldn't create "${username}"`
  }
}
/**
 * Getter of update action Labels.
 * @param {string} username - user name.
 * @returns {object} - {pending, resolved, rejected}.
 */
const updatingLabel = (username: string): INotifyLabel => {
  return {
    pending: `Updating "${username}"`,
    resolved: `"${username}" successfully updated!`,
    rejected: `Couldn't update "${username}"`
  }
}
/**
 * Getter of delete action Labels.
 * @param {string} username - user name.
 * @returns {object} - {pending, resolved, rejected}.
 */
const deletingLabel = (username: string): INotifyLabel => {
  return {
    pending: `Deleting "${username}"`,
    resolved: `"${username}" successfully deleted!`,
    rejected: `Couldn't delete "${username}"`
  }
}
/**
 * Getter of delete several action Labels.
 * @returns {object} - {pending, resolved, rejected}.
 */
const deletingsLabel = (): INotifyLabel => {
  return {
    pending: 'Deleting selected users',
    resolved: 'Users successfully deleted!',
    rejected: "Couldn't delete selected users"
  }
}
export { creatingLabel, updatingLabel, deletingLabel, deletingsLabel }
