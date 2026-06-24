import { IUnknownObjectKeys } from '@interfaces/Interfaces'
import { IPaginatedQuery } from '@ateme/cathodic-ui/src/interfaces/Table'

/**
 * Compare two objects and return the differences.
 * @param {object} obj1 - The first object to compare.
 * @param {object} obj2 - The second object to compare.
 * @returns {object} - The differences between the two objects.
 */
export const compareObjects = (obj1: IUnknownObjectKeys, obj2: IUnknownObjectKeys): IUnknownObjectKeys => {
  const result: IUnknownObjectKeys = {}

  for (const key in obj2) {
    if (Object.prototype.hasOwnProperty.call(obj2, key)) {
      if (Object.prototype.hasOwnProperty.call(obj1, key)) {
        if (obj2[key] !== obj1[key]) {
          result[key] = obj2[key]
        }
      } else {
        result[key] = obj2[key]
      }
    }
  }

  return result
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const isEmpty = (value: any): boolean => {
  if (value == null) {
    return true
  }

  if (typeof value === 'string' || Array.isArray(value)) {
    return value.length === 0
  }

  if (typeof value === 'object') {
    return Object.keys(value).length === 0
  }

  return false
}

/**
 * Get the readable backend range of the paginated query returned by cathodic-ui table.
 * @param {IPaginatedQuery} paginatedQuery - The query of the paginated table.
 * @param {number} max - The maximum number of items in the database.
 * @returns {string} - The range to use in the backend query "start-end", example "0-10".
 */
export const getRangeFromPaginatedQuery = (paginatedQuery: IPaginatedQuery, max: number): string => {
  let start = (paginatedQuery.pageNumber - 1) * paginatedQuery.rowPerSearch
  if (start >= max) {
    start = 0
  }
  const end = start + paginatedQuery.rowPerSearch - 1
  if (end >= max && max !== 0) {
    return `${start}-${max - 1}`
  }
  return `${start}-${end}`
}
