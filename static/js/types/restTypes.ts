export type RestState<T> = {
  data?: T
  error?: any
  processing: boolean
  loaded: boolean
  getStatus?: string
}

export type Endpoint = {
  name: string
  namespaceOnUsername: boolean
  checkNoSpinner: boolean
  // Flow read `string|(...args: any) => string` as a union with the function
  // type; TypeScript needs the parentheses or it parses as a function
  // returning `string | string`.
  getUrl?: string | ((...args: any[]) => string)
  postUrl?: string | ((...args: any[]) => string)
  patchUrl?: string | ((...args: any[]) => string)
  getOptions?: (...args: any[]) => Record<string, any>
  postOptions?: (...args: any[]) => Record<string, any>
  patchOptions?: (...args: any[]) => Record<string, any>
  extraActions?: Record<string, any>
  getPrefix?: string
  postPrefix?: string
  patchPrefix?: string
  getFunc?: (...args: any[]) => any
  postFunc?: (...args: any[]) => any
  patchFunc?: (...args: any[]) => any
  verbs: Array<string>
  initialState?: Record<string, any>
  usernameInitialState?: Record<string, any>
}
