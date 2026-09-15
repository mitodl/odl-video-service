// @flow
import type { Action } from "../flow/reduxTypes"

import {
  INIT_COLLECTION_FORM,
  SET_COLLECTION_TITLE,
  SET_COLLECTION_DESC,
  SET_COLLECTION_DESC_FORMAT,
  SET_VIEW_CHOICE,
  SET_VIEW_LISTS,
  SET_ADMIN_CHOICE,
  SET_ADMIN_LISTS,
  SET_EDX_COURSE_ID,
  SET_OWNER_ID,
  SET_SELECTED_VIDEO_KEY,
  SET_IS_NEW,
  CLEAR_COLLECTION_FORM,
  SET_COLLECTION_FORM_ERRORS
} from "../actions/collectionUi"
import { DESCRIPTION_FORMAT_HTML, DESCRIPTION_FORMAT_TEXT } from "../constants"
import { PERM_CHOICE_NONE } from "../lib/dialog"
import { getFormKey } from "../lib/collection"

import type { CollectionUiState } from "../flow/collectionTypes"

export const INITIAL_COLLECTION_FORM_STATE = {
  key:                "",
  title:              "",
  description:        "",
  // Plain text until the record says otherwise; see DESCRIPTION_FORMAT_TEXT.
  description_format: DESCRIPTION_FORMAT_TEXT,
  viewChoice:         PERM_CHOICE_NONE,
  viewLists:          null,
  adminChoice:        PERM_CHOICE_NONE,
  adminLists:         null,
  edxCourseId:        "",
  ownerId:            null
}

/*
 * A collection that does not exist yet starts as rich text.
 *
 * The plain-text default and the "Use formatting" button exist to protect
 * descriptions that were written before rich text did - opening one in the
 * editor parses it as HTML and collapses the author's line breaks, so the
 * conversion has to be a deliberate choice. A collection being created has no
 * such description: the field is empty, there is nothing to lose, and an author
 * writing their first words should not have to ask for formatting.
 */
export const INITIAL_NEW_COLLECTION_FORM_STATE = {
  ...INITIAL_COLLECTION_FORM_STATE,
  description_format: DESCRIPTION_FORMAT_HTML
}

export const INITIAL_UI_STATE = {
  newCollectionForm:  INITIAL_NEW_COLLECTION_FORM_STATE,
  editCollectionForm: INITIAL_COLLECTION_FORM_STATE,
  isNew:              true,
  selectedVideoKey:   null
}

const updateCollectionForm = (
  state: CollectionUiState,
  key: string,
  newValue: ?string
) => ({
  ...state,
  [getFormKey(state.isNew)]: {
    ...state[getFormKey(state.isNew)],
    [key]: newValue
  }
})

const reducer = (
  state: CollectionUiState = INITIAL_UI_STATE,
  action: Action<any, null>
) => {
  switch (action.type) {
  case INIT_COLLECTION_FORM:
    return {
      ...state,
      [getFormKey(state.isNew)]: {
        ...state[getFormKey(state.isNew)],
        ...action.payload
      }
    }
  case SET_COLLECTION_TITLE:
    return updateCollectionForm(state, "title", action.payload)
  case SET_COLLECTION_DESC:
    return updateCollectionForm(state, "description", action.payload)
  case SET_COLLECTION_DESC_FORMAT:
    return updateCollectionForm(state, "description_format", action.payload)
  case SET_VIEW_CHOICE:
    return updateCollectionForm(state, "viewChoice", action.payload)
  case SET_VIEW_LISTS:
    return updateCollectionForm(state, "viewLists", action.payload)
  case SET_ADMIN_CHOICE:
    return updateCollectionForm(state, "adminChoice", action.payload)
  case SET_ADMIN_LISTS:
    return updateCollectionForm(state, "adminLists", action.payload)
  case SET_EDX_COURSE_ID:
    return updateCollectionForm(state, "edxCourseId", action.payload)
  case SET_OWNER_ID:
    return updateCollectionForm(state, "ownerId", action.payload)
  case SET_SELECTED_VIDEO_KEY:
    return { ...state, selectedVideoKey: action.payload }
  case SET_IS_NEW:
    return { ...state, isNew: action.payload }
  case CLEAR_COLLECTION_FORM:
    return INITIAL_UI_STATE
  case SET_COLLECTION_FORM_ERRORS:
    return {
      ...state,
      errors: action.payload.errors
    }
  default:
    return state
  }
}

export default reducer
