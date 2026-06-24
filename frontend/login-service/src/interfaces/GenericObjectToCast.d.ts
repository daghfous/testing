// All type in this file must be replace by real value or schema

/* eslint-disable  @typescript-eslint/no-explicit-any */
export type GenericOnlyObjectToCast = { [key: string]: any }

export type GenericObjectToCast = GenericOnlyObjectToCast | string | number | boolean
