// @flow
/* global SETTINGS: true */
import React from "react"
import sinon from "sinon"
import { screen, fireEvent, render } from "@testing-library/react"
import { assert } from "chai"
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
import renderWithProviders from "../testUtils/renderWithProviders"

describe("CollectionListPage", () => {
  let sandbox, store, collections, listenForActions, collectionsPagination

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    store = configureTestStore(rootReducer)
    listenForActions = store.createListenForActions()
    collections = [makeCollection(), makeCollection(), makeCollection()]
    // Add owner_info to each collection
    collections.forEach(collection => {
      collection.owner_info = {
        id:       collection.owner,
        username: collection.owner_info.username,
        email:    collection.owner_info.email
      }
    })
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
    let rendered

    await listenForActions(
      [
        actions.collectionsList.get.requestType,
        actions.collectionsList.get.successType,
        collectionsPaginationActions.constants.REQUEST_GET_PAGE
      ],
      () => {
        rendered = renderWithProviders(
          <MemoryRouter>
            <Route>
              <CollectionListPage {...props} />
            </Route>
          </MemoryRouter>,
          { store }
        )
      }
    )
    if (!rendered) throw new Error("Never will happen, make flow happy")
    return rendered
  }

  const renderUnconnectedPage = (props = {}) => {
    props = { collectionsPagination, ...props }
    return render(<UnconnectedCollectionListPage {...props} />)
  }

  it("doesn't show the create collection button if SETTINGS.is_app_admin is false", async () => {
    SETTINGS.is_app_admin = false
    await renderPage()
    assert.isNull(screen.queryByText(/Create New Collection/i))
  })

  it("opens a dialog to create a new collection", async () => {
    SETTINGS.is_app_admin = true
    await renderPage()
    const state = await listenForActions([SHOW_DIALOG, SET_IS_NEW], () => {
      fireEvent.click(screen.getByText(/Create New Collection/i))
    })
    assert.isTrue(state.collectionUi.isNew)
    assert.isTrue(state.commonUi.dialogVisibility[DIALOGS.COLLECTION_FORM])
  })

  it("has a toolbar whose handler will dispatch an action to open the drawer", async () => {
    const { container } = await renderPage()
    fireEvent.click(container.querySelector(".menu-button"))
    assert.isTrue(store.getState().commonUi.drawerOpen)
  })

  describe("when page has loaded", () => {
    it("has video counts per collection", async () => {
      const { container } = await renderPage()
      const counts = container.querySelectorAll(
        ".mdc-list-item__secondary-text"
      )
      assert.equal(
        counts[0].textContent,
        `${collections[0].video_count} Videos | Owner: ${collections[0].owner_info.username}`
      )
    })
  })

  it("has paginator", async () => {
    const { container } = await renderPage()
    const paginator = container.querySelectorAll(".paginator")
    assert.equal(paginator.length, 1)
  })

  describe("when page.status is loading", () => {
    it("renders loading indicator", () => {
      collectionsPagination.currentPageData.status = "LOADING"
      renderUnconnectedPage()
      assert.exists(screen.getByText(/Loading/i))
    })
  })

  describe("when page.status is error", () => {
    it("renders error indicator", () => {
      collectionsPagination.currentPageData.status = "ERROR"
      renderUnconnectedPage()
      assert.exists(screen.getByText(/unable to load the data/i))
    })
  })
})
