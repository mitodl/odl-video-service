// @flow
/* global SETTINGS: false */
import React from "react"
import { assert } from "chai"
import { mount } from "enzyme"
import sinon from "sinon"
import configureTestStore from "redux-asserts"
import { Provider } from "react-redux"
import rootReducer from "../../reducers"
import * as api from "../../lib/api"
import { actions } from "../../actions"
import Drawer from "./Drawer"
import { makeCollection } from "../../factories/collection"
import { makeCollectionUrl } from "../../lib/urls"
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
    let wrapper
    await listenForActions(
      [
        actions.collectionsList.get.requestType,
        actions.collectionsList.get.successType
      ],
      () => {
        wrapper = mount(
          <Provider store={store}>
            <Drawer {...props} />
          </Provider>
        )
      }
    )
    if (!wrapper) {
      throw new Error("Never will happen, make flow happy")
    }
    wrapper.update()
    return wrapper
  }

  it("drawer element is rendered with the correct user", async () => {
    const wrapper = await renderDrawer()
    const drawerNode = wrapper.find(".mdc-list-item .mdc-link").at(0)
    assert.isTrue(drawerNode.text().startsWith("foo@mit.edu"))
  })

  it("shows the username if the email is not present", async () => {
    SETTINGS.email = null
    const wrapper = await renderDrawer()
    const drawerNode = wrapper.find(".mdc-list-item .mdc-link").at(0)
    assert.isTrue(drawerNode.text().startsWith("foo_user"))
  })

  it("shows logout button", async () => {
    const wrapper = await renderDrawer()
    assert.isTrue(wrapper.find(".mdc-list-item.logout").exists())
  })

  describe("when user is not logged", () => {
    let wrapper

    beforeEach(async () => {
      SETTINGS.email = null
      SETTINGS.user = null
      wrapper = await renderDrawer()
    })

    it("shows a message if the user is not logged in", async () => {
      const drawerNode = wrapper.find(".mdc-list-item .mdc-link").at(0)
      assert.isTrue(drawerNode.text().startsWith("Not logged in"))
    })

    it("does not show log out button", () => {
      assert.isFalse(wrapper.find(".mdc-list-item.logout").exists())
    })
  })

  it("drawer element is rendered with collections", async () => {
    const wrapper = await renderDrawer()
    const drawerNode = wrapper.find(".mdc-list-item .mdc-link").at(2)
    assert.equal(drawerNode.props().href, "/logout/")
    assert.isTrue(drawerNode.text().endsWith("Log out"))
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
      const wrapper = await renderDrawer()
      const items = wrapper.find(".mdc-list-item .mdc-list-item--activated")
      assert.equal(items.length, 10)
      ;[0, 1, 3, 9].forEach(function(col) {
        const drawerNode = items.at(col)
        assert.equal(
          drawerNode.text(),
          `${collections[col].title} (${collections[col].video_count})`
        )
        assert.equal(
          drawerNode.props().href,
          makeCollectionUrl(collections[col].key)
        )
      })
    })

    it("has 'more...' button that links to collections page", async () => {
      const wrapper = await renderDrawer()
      const moreButton = wrapper.find(".more-collections-button")
      assert.equal(moreButton.length, 1)
      assert.equal(moreButton.prop("href"), "/collections/")
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
      const wrapper = await renderDrawer()
      assert.isFalse(wrapper.find(".more-collections-button").exists())
    })
  })

  it("drawer element is rendered with a logout link", async () => {
    const wrapper = await renderDrawer()
    const drawerNode = wrapper.find(".mdc-list-item .mdc-link").at(2)
    assert.equal(drawerNode.props().href, "/logout/")
    assert.isTrue(drawerNode.text().endsWith("Log out"))
  })

  it("fetches requirements on load", async () => {
    await renderDrawer()
    sinon.assert.calledWith(getCollectionsStub)
  })

  it("closes the drawer if the user is clicked", async () => {
    const onDrawerCloseStub = sandbox.stub()
    const wrapper = await renderDrawer({
      onDrawerClose: onDrawerCloseStub
    })
    wrapper
      .find("#collapse_item")
      .instance()
      .click()
    sinon.assert.calledWith(onDrawerCloseStub)
  })
})
