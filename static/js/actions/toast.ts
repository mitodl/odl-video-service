import { createAction } from "redux-actions"

const qualifiedName = (name: string) => `TOAST_${name}`
/*
 * Object literals rather than assignment onto `{}`. The mutation style only
 * typechecked under Flow because nothing was reading these files; TypeScript
 * infers `{}` and rejects every subsequent property. Literals also mean each
 * `constants.FOO` is checked at its call sites instead of resolving to `any`.
 */
export const constants = {
  ADD_MESSAGE:    qualifiedName("ADD_MESSAGE"),
  REMOVE_MESSAGE: qualifiedName("REMOVE_MESSAGE")
}

export const actionCreators = {
  addMessage:    createAction(constants.ADD_MESSAGE),
  removeMessage: createAction(constants.REMOVE_MESSAGE)
}
