// @flow
import sinon from "sinon"
import configureTestStore from "redux-asserts"
import { assert } from "chai"
import _ from "lodash"

import rootReducer from "../reducers"
import {
  setDrawerOpen,
  showDialog,
  hideDialog,
  showMenu,
  hideMenu,
  toggleFAQVisibility
} from "../actions/commonUi"
import { INITIAL_UI_STATE } from "./commonUi"
import { createAssertReducerResultState } from "../util/test_utils"
import { DIALOGS } from "../constants"

describe("CommonUi", () => {
  let sandbox, assertReducerResultState, store

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    assertReducerResultState = createAssertReducerResultState(
      store,
      state => state.commonUi
    )
    store = configureTestStore(rootReducer)
  })

  afterEach(() => {
    sandbox.restore()
  })

  it("should open the drawer in the UI", () => {
    store.dispatch(setDrawerOpen(true))
    assert.include(store.getState().commonUi, { drawerOpen: true })
  })

  it("should close the drawer in the UI", () => {
    store.dispatch(setDrawerOpen(false))
    assert.deepEqual(store.getState().commonUi, INITIAL_UI_STATE)
  })

  it("setting the drawer visibility changes state", () => {
    assertReducerResultState(setDrawerOpen, ui => ui.drawerOpen, false)
  })

  it("has actions that open and close dialogs", () => {
    _.mapKeys(DIALOGS, dialogKey => {
      store.dispatch(showDialog(dialogKey))
      assert.deepEqual(
        store.getState().commonUi.dialogVisibility[dialogKey],
        true
      )
      store.dispatch(hideDialog(dialogKey))
      assert.deepEqual(
        store.getState().commonUi.dialogVisibility[dialogKey],
        false
      )
    })
  })

  it("has actions that open and close menus", () => {
    const formObj = { key: "key", title: "title", description: "description" }
    store.dispatch(showMenu(formObj))
    assert.deepEqual(store.getState().commonUi.menuVisibility[formObj], true)
    store.dispatch(hideMenu(formObj))
    assert.deepEqual(store.getState().commonUi.menuVisibility[formObj], false)
  })

  it("should have initial state for FAQ visibility", () => {
    assert.deepEqual(store.getState().commonUi.FAQVisibility, new Map())
  })

  it("should let you toggle whether an FAQ is shown or not", () => {
    assert.equal(
      store.getState().commonUi.FAQVisibility.get("my faq"),
      undefined
    )
    store.dispatch(toggleFAQVisibility("my faq"))
    assert.equal(store.getState().commonUi.FAQVisibility.get("my faq"), true)
    store.dispatch(toggleFAQVisibility("my faq"))
    assert.equal(store.getState().commonUi.FAQVisibility.get("my faq"), false)
  })
})
