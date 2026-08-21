// @flow
/* global SETTINGS: false */
import React from "react"
import { assert } from "chai"
import { fireEvent } from "@testing-library/react"
import sinon from "sinon"
import configureTestStore from "redux-asserts"
import rootReducer from "../../reducers"
import * as api from "../../lib/api"
import { actions } from "../../actions"
import Drawer from "./Drawer"
import { makeCollection } from "../../factories/collection"
import { makeCollectionUrl } from "../../lib/urls"
import renderWithProviders from "../../testUtils/renderWithProviders"
import type { Collection } from "../../flow/collectionTypes"

describe("Drawer", () => {
  let sandbox,
    store,
    collections: Array<Collection>,
    listenForActions,
    getCollectionsStub
  beforeEach(() => {
    sandbox = sinon.createSandbox()
    store = configureTestStore(rootReducer)
    SETTINGS.email = "foo@mit.edu"
    SETTINGS.user = "foo_user"
    collections = [makeCollection(), makeCollection()]
    listenForActions = store.createListenForActions()
    getCollectionsStub = sandbox
      .stub(api, "getCollections")
      .returns(Promise.resolve({ results: collections }))
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderDrawer = async (props = {}) => {
    let result
    await listenForActions(
      [
        actions.collectionsList.get.requestType,
        actions.collectionsList.get.successType
      ],
      () => {
        result = renderWithProviders(<Drawer {...props} />, { store })
      }
    )
    if (!result) {
      throw new Error("Never will happen, make flow happy")
    }
    return result
  }

  it("drawer element is rendered with the correct user", async () => {
    const { container } = await renderDrawer()
    const drawerNode = container.querySelectorAll(".mdc-list-item.mdc-link")[0]
    assert.isTrue(drawerNode.textContent.startsWith("foo@mit.edu"))
  })

  it("shows the username if the email is not present", async () => {
    SETTINGS.email = null
    const { container } = await renderDrawer()
    const drawerNode = container.querySelectorAll(".mdc-list-item.mdc-link")[0]
    assert.isTrue(drawerNode.textContent.startsWith("foo_user"))
  })

  it("shows logout button", async () => {
    const { container } = await renderDrawer()
    assert.isNotNull(container.querySelector(".mdc-list-item.logout"))
  })

  describe("when user is not logged", () => {
    let container

    beforeEach(async () => {
      SETTINGS.email = null
      SETTINGS.user = null
      ;({ container } = await renderDrawer())
    })

    it("shows a message if the user is not logged in", () => {
      const drawerNode = container.querySelectorAll(
        ".mdc-list-item.mdc-link"
      )[0]
      assert.isTrue(drawerNode.textContent.startsWith("Not logged in"))
    })

    it("does not show log out button", () => {
      assert.isNull(container.querySelector(".mdc-list-item.logout"))
    })
  })

  it("drawer element is rendered with collections", async () => {
    const { container } = await renderDrawer()
    const drawerNode = container.querySelectorAll(".mdc-list-item.mdc-link")[2]
    assert.equal(drawerNode.getAttribute("href"), "/logout/")
    assert.isTrue(drawerNode.textContent.endsWith("Log out"))
  })

  it("drawer element is rendered with a logout link", async () => {
    const { container } = await renderDrawer()
    const drawerNode = container.querySelectorAll(".mdc-list-item.mdc-link")[2]
    assert.equal(drawerNode.getAttribute("href"), "/logout/")
    assert.isTrue(drawerNode.textContent.endsWith("Log out"))
  })

  describe("when there are > 10 collections", () => {
    beforeEach(() => {
      const numCollections = 20
      collections = [...Array(numCollections).keys()].map(() =>
        makeCollection()
      )
      getCollectionsStub.returns(Promise.resolve({ results: collections }))
    })

    it("drawer element is rendered with max of 10 collections", async () => {
      const { container } = await renderDrawer()
      const items = container.querySelectorAll(
        ".mdc-list-item.mdc-list-item--activated"
      )
      assert.equal(items.length, 10)
      ;[0, 1, 3, 9].forEach(function(col) {
        const drawerNode = items[col]
        assert.equal(
          drawerNode.textContent,
          `${collections[col].title} (${collections[col].video_count})`
        )
        assert.equal(
          drawerNode.getAttribute("href"),
          makeCollectionUrl(collections[col].key)
        )
      })
    })

    it("has 'more...' button that links to collections page", async () => {
      const { container } = await renderDrawer()
      const moreButton = container.querySelector(".more-collections-button")
      assert.isNotNull(moreButton)
      assert.equal(moreButton.getAttribute("href"), "/collections/")
    })
  })

  describe("when there are <= 10 collections", () => {
    beforeEach(() => {
      const numCollections = 10
      collections = [...Array(numCollections).keys()].map(() =>
        makeCollection()
      )
      getCollectionsStub.returns(Promise.resolve({ results: collections }))
    })

    it("does not have 'more...' button", async () => {
      const { container } = await renderDrawer()
      assert.isNull(container.querySelector(".more-collections-button"))
    })
  })

  it("fetches requirements on load", async () => {
    await renderDrawer()
    sinon.assert.calledWith(getCollectionsStub)
  })

  it("closes the drawer if the user is clicked", async () => {
    const onDrawerCloseStub = sandbox.stub()
    const { container } = await renderDrawer({
      onDrawerClose: onDrawerCloseStub
    })
    fireEvent.click(container.querySelector("#collapse_item"))
    sinon.assert.calledWith(onDrawerCloseStub)
  })

  describe("open prop transitions", () => {
    // componentDidUpdate replaced componentWillReceiveProps here.
    // Drawer_test.js never toggled `open` before, so a regression in this
    // comparison would still pass every other test in this file.
    //
    // The old Enzyme version needed a stateful `Harness` component solely so
    // a *real* prop change would flow down through the redux-connect()'d
    // Drawer -- Enzyme's wrapper.setProps() only re-renders the mount root
    // (the Harness), not a nested connected component. RTL's rerender()
    // re-renders new props through the existing tree (still wrapped in the
    // same Provider, via renderWithProviders), so no Harness is needed.
    it("updates the underlying MDC drawer's open state as the open prop toggles, including a reopen", async () => {
      const { container, rerender } = await renderDrawer({
        open:          false,
        onDrawerClose: () => {}
      })
      const drawerRoot = container.querySelector(".mdc-drawer")
      assert.isFalse(drawerRoot.classList.contains("mdc-drawer--open"))

      rerender(<Drawer open={true} onDrawerClose={() => {}} />)
      assert.isTrue(drawerRoot.classList.contains("mdc-drawer--open"))

      rerender(<Drawer open={false} onDrawerClose={() => {}} />)
      assert.isFalse(drawerRoot.classList.contains("mdc-drawer--open"))

      rerender(<Drawer open={true} onDrawerClose={() => {}} />)
      assert.isTrue(drawerRoot.classList.contains("mdc-drawer--open"))
    })
  })
})
