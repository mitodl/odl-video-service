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
import { CollectionListPage as UnconnectedCollectionListPage } from "./CollectionListPage"

import * as api from "../lib/api"
import { actions } from "../actions"
import * as collectionsPaginationActions from "../actions/collectionsPagination"
import { SET_IS_NEW } from "../actions/collectionUi"
import { SHOW_DIALOG } from "../actions/commonUi"
import rootReducer from "../reducers"
import { makeCollection } from "../factories/collection"
import { DIALOGS } from "../constants"

describe("CollectionListPage", () => {
  let sandbox, store, collections, listenForActions, collectionsPagination

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    collections = [makeCollection(), makeCollection(), makeCollection()]
    collectionsPagination = {
      currentPage:     1,
      currentPageData: {
        status: "LOADED",
        collections
      }
    }
    sandbox
      .stub(api, "getCollections")
      .returns(Promise.resolve({ results: collections }))
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderPage = async (props = {}) => {
    let wrapper

    await listenForActions(
      [
        actions.collectionsList.get.requestType,
        actions.collectionsList.get.successType,
        collectionsPaginationActions.constants.REQUEST_GET_PAGE
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

  const renderUnconnectedPage = (props = {}) => {
    props = { collectionsPagination, ...props }
    const wrapper = mount(<UnconnectedCollectionListPage {...props} />)
    if (!wrapper) throw new Error("Never will happen, make flow happy")
    wrapper.update()
    return wrapper
  }

  it("doesn't show the create collection button if SETTINGS.is_app_admin is false", async () => {
    SETTINGS.is_app_admin = false
    const wrapper = await renderPage()
    assert.lengthOf(wrapper.find(".create-collection-button"), 0)
  })

  it("opens a dialog to create a new collection", async () => {
    SETTINGS.is_app_admin = true
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

  describe("when page has loaded", () => {
    it("has video counts per collection", async () => {
      const wrapper = await renderPage()
      const counts = wrapper.find(".mdc-list-item__secondary-text")
      assert.equal(counts.at(0).text(), `${collections[2].video_count} Videos`)
    })
  })

  it("has paginator", async () => {
    const wrapper = await renderPage()
    const paginator = wrapper.find("Paginator")
    assert.equal(paginator.length, 1)
  })

  describe("when page.status is loading", () => {
    it("renders loading indicator", () => {
      collectionsPagination.currentPageData.status = "LOADING"
      const wrapper = renderUnconnectedPage()
      assert.exists(wrapper.find("LoadingIndicator"))
    })
  })

  describe("when page.status is error", () => {
    it("renders error indicator", () => {
      collectionsPagination.currentPageData.status = "ERROR"
      const wrapper = renderUnconnectedPage()
      assert.isTrue(wrapper.find("ErrorMessage").exists())
    })
  })
})
