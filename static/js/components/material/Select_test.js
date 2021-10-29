// @flow
/* global SETTINGS: false */
import React from "react"
import { assert } from "chai"
import { mount } from "enzyme"
import sinon from "sinon"
import configureTestStore from "redux-asserts"
import { Provider } from "react-redux"
import rootReducer from "../../reducers"
import Select from "./Select"

describe("Select", () => {
  let sandbox, store
  beforeEach(() => {
    sandbox = sinon.createSandbox()
    store = configureTestStore(rootReducer)
    SETTINGS.is_edx_course_admin = true
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderSelect = async (props = {}) => {
    return mount(
      <Provider store={store}>
        <Select {...props} />
      </Provider>
    )
  }

  it("select element is rendered with no selected edx endpoint", async () => {
    const wrapper = await renderSelect({
      selectedEndpoint: -1,
      menuItems:        []
    })
    const selectNode = wrapper.find(".mdc-select__label").at(0)
    assert.isTrue(selectNode.text().startsWith("Select Edx Endpoint"))
    assert.isNotTrue(selectNode.hasClass("mdc-select__label--float-above"))
  })

  it("select element is rendered with selected edx endpoint", async () => {
    const wrapper = await renderSelect({
      selectedEndpoint: 3,
      menuItems:        []
    })
    const selectNode = wrapper.find(".mdc-select__label").at(0)
    assert.isTrue(selectNode.hasClass("mdc-select__label--float-above"))
  })
})
