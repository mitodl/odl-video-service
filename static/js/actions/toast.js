// @flow
import { createAction } from "redux-actions"

const qualifiedName = (name: string) => `TOAST_${name}`
const constants = {}
const actionCreators = {}

constants.ADD_MESSAGE = qualifiedName("ADD_MESSAGE")
actionCreators.addMessage = createAction(constants.ADD_MESSAGE)

constants.REMOVE_MESSAGE = qualifiedName("REMOVE_MESSAGE")
actionCreators.removeMessage = createAction(constants.REMOVE_MESSAGE)

export { actionCreators, constants }
