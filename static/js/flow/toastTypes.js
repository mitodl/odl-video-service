// @flow
//
export type ToastMessage = {
  key: string,
  content: string,
  icon?: string
}

export type ToastState = {
  messages: Array<ToastMessage>
};
