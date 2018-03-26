// @flow
/* global SETTINGS: true */
import React from "react"
import sinon from "sinon"
import { mount } from "enzyme"
import { assert } from "chai"
import { Provider } from "react-redux"
import configureTestStore from "redux-asserts"
import { MemoryRouter, Route } from "react-router"

import CollectionListPage from "./CollectionListPage"

import * as api from "../lib/api"
import { actions } from "../actions"
import { SET_IS_NEW } from "../actions/collectionUi"
import { SHOW_DIALOG } from "../actions/commonUi"
import rootReducer from "../reducers"
import { makeCollection } from "../factories/collection"
import { DIALOGS } from "../constants"

describe("CollectionListPage", () => {
  let sandbox, store, collections, listenForActions

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    collections = [makeCollection(), makeCollection(), makeCollection()]

    sandbox.stub(api, "getCollections").returns(Promise.resolve(collections))
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderPage = async (props = {}) => {
    let wrapper

    await listenForActions(
      [
        actions.collectionsList.get.requestType,
        actions.collectionsList.get.successType
      ],
      () => {
        wrapper = mount(
          <MemoryRouter>
            <Route>
              <Provider store={store}>
                <CollectionListPage {...props} />
              </Provider>
            </Route>
          </MemoryRouter>
        )
      }
    )
    if (!wrapper) throw new Error("Never will happen, make flow happy")
    wrapper.update()
    return wrapper
  }

  it("loads the collections on load", async () => {
    await renderPage()
    assert.deepEqual(store.getState().collectionsList.data, collections)
  })

  it("doesn't show the create collection button if SETTINGS.editable is false", async () => {
    SETTINGS.editable = false
    const wrapper = await renderPage()
    assert.lengthOf(wrapper.find(".create-collection-button"), 0)
  })

  it("opens a dialog to create a new collection", async () => {
    SETTINGS.editable = true
    const wrapper = await renderPage()
    const state = await listenForActions([SHOW_DIALOG, SET_IS_NEW], () => {
      wrapper
        .find(".collection-list-content .create-collection-button")
        .simulate("click")
    })
    assert.isTrue(state.collectionUi.isNew)
    assert.isTrue(state.commonUi.dialogVisibility[DIALOGS.COLLECTION_FORM])
  })

  it("has a toolbar whose handler will dispatch an action to open the drawer", async () => {
    const wrapper = await renderPage()
    wrapper.find(".menu-button").simulate("click")
    assert.isTrue(store.getState().commonUi.drawerOpen)
  })

  it("has video counts per collection", async () => {
    const wrapper = await renderPage()
    const counts = wrapper.find(".mdc-list-item__secondary-text")
    assert.equal(counts.at(0).text(), `${collections[2].video_count} Videos`)
  })
})
