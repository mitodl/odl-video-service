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
import * as edxEndpointActions from "../actions/edxEndpoints"
import { SET_IS_NEW } from "../actions/collectionUi"
import { SHOW_DIALOG } from "../actions/commonUi"
import rootReducer from "../reducers"
import { makeCollection } from "../factories/collection"
import { DIALOGS } from "../constants"
import { makeEdxEndpointList } from "../factories/edxEndpoints"

describe("CollectionListPage", () => {
  let sandbox, dispatch, store, collections, listenForActions, collectionsPagination, edxEndpoints

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    dispatch = sinon.fake()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    collections = [makeCollection(), makeCollection(), makeCollection()]
    collectionsPagination = {
      currentPage:     1,
      numPages:        3,
      setCurrentPage:  sandbox.stub(),
      currentPageData: {
        status: "LOADED",
        collections
      }
    }
    edxEndpoints = {
      data:   makeEdxEndpointList(),
      status: "LOADED"
    }
    sandbox
      .stub(api, "getCollections")
      .returns(Promise.resolve({ results: collections }))
    sandbox
      .stub(api, "getEdxEndpoints")
      .returns(Promise.resolve(edxEndpoints))
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
        collectionsPaginationActions.constants.REQUEST_GET_PAGE,
        edxEndpointActions.constants.REQUEST_GET_ENDPOINTS,
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
    props = { collectionsPagination, edxEndpoints, dispatch, ...props }
    const wrapper = mount(
      <MemoryRouter>
        <UnconnectedCollectionListPage {...props} />
      </MemoryRouter>
    )
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

  describe("when page.status is loading", () => {
    it("renders loading indicator", () => {
      collectionsPagination.currentPageData.status = "LOADING"
      const wrapper = renderUnconnectedPage()
      assert.exists(wrapper.find("LoadingIndicator"))
    })
  })

  describe("when page.status is error", () => {
    it("renders error indicator", () => {
      edxEndpoints.status = "ERROR"
      const wrapper = renderUnconnectedPage()
      assert.isTrue(wrapper.find("ErrorMessage").exists())
    })
  })

  describe("default view mode - endpoints", () => {
    it("renders edx endpoints list by default", () => {
      const wrapper = renderUnconnectedPage()
      assert.exists(wrapper.find(".edx-endpoints-container"))
      assert.isTrue(wrapper.find(".endpoint-list").exists())
      assert.isTrue(wrapper.find(".endpoint-item").exists())

      if (edxEndpoints.data) {
        // +1 for "All Collections" entry
        assert.equal(wrapper.find(".endpoint-item").length, edxEndpoints.data.length + 1)
      }
    })
  })

  describe("selecting an endpoint", () => {
    it("switches to collections view when an endpoint is clicked", () => {
      const wrapper = renderUnconnectedPage()
      const collectionListPage = wrapper.find(UnconnectedCollectionListPage).instance()
      assert.equal(collectionListPage.state.viewMode, "endpoints")
      wrapper.find(".endpoint-item").at(0).simulate("click")
      assert.equal(collectionListPage.state.viewMode, "collections")
      wrapper.update()
      assert.exists(wrapper.find(".collection-list"))
    })

    it("sets URL parameters when an endpoint is selected", () => {
      const wrapper = renderUnconnectedPage()
      const firstEndpoint = wrapper.find(".endpoint-item").at(1) // Using 1 to skip "All Collections"
      // Mock window.history.pushState
      const historyPushStateSpy = sinon.spy(window.history, "pushState")
      firstEndpoint.simulate("click")
      assert.isTrue(historyPushStateSpy.called)
      historyPushStateSpy.restore()
    })
  })

  describe("collections view mode", () => {
    it("displays collections with video counts", () => {
      const wrapper = renderUnconnectedPage()
      wrapper.find(".endpoint-item").at(0).simulate("click")
      wrapper.update()

      assert.exists(wrapper.find(".collection-list"))
      const collectionItems = wrapper.find(".collection-list .mdc-list-item")
      assert.equal(collectionItems.length, collections.length)

      wrapper.find(".mdc-list-item__secondary-text").forEach(node => {
        assert.include(node.text(), "Videos")
      })
      const counts = wrapper.find(".mdc-list-item__secondary-text")
      assert.equal(counts.at(0).text(), `${collections[2].video_count} Videos`)
    })

    it("shows a search input when in collections view", () => {
      const wrapper = renderUnconnectedPage()

      wrapper.find(".endpoint-item").at(0).simulate("click")
      wrapper.update()

      assert.exists(wrapper.find(".collection-search"))
      assert.exists(wrapper.find(".collection-search input"))
    })

    it("shows a back button to return to endpoints view", () => {
      const wrapper = renderUnconnectedPage()

      wrapper.find(".endpoint-item").at(0).simulate("click")
      wrapper.update()

      assert.exists(wrapper.find(".back-to-endpoints"))
      wrapper.find(".back-to-endpoints a").simulate("click")
      assert.equal(wrapper.find(UnconnectedCollectionListPage).instance().state.viewMode, "endpoints")
    })
  })

  describe("pagination in collections view", () => {
    it("renders a paginator when in collections view", () => {
      const wrapper = renderUnconnectedPage()

      wrapper.find(".endpoint-item").at(0).simulate("click")
      wrapper.update()

      assert.exists(wrapper.find("Paginator"))
    })
  })
})
