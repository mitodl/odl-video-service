// @flow
import { createAction } from "redux-actions"

export const qualifiedName = (name: string) => `UI_${name}`

export const SET_DRAWER_OPEN = qualifiedName("SET_DRAWER_OPEN")
export const setDrawerOpen = createAction(SET_DRAWER_OPEN)

export const SHOW_DIALOG = qualifiedName("SHOW_DIALOG")
export const showDialog = createAction(SHOW_DIALOG)

export const HIDE_DIALOG = qualifiedName("HIDE_DIALOG")
export const hideDialog = createAction(HIDE_DIALOG)

export const SHOW_MENU = qualifiedName("SHOW_MENU")
export const showMenu = createAction(SHOW_MENU)

export const HIDE_MENU = qualifiedName("HIDE_MENU")
export const hideMenu = createAction(HIDE_MENU)

export const TOGGLE_FAQ_VISIBILITY = qualifiedName("TOGGLE_FAQ_VISIBILITY")
export const toggleFAQVisibility = createAction(TOGGLE_FAQ_VISIBILITY)
