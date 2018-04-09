// @flow
import React from "react"
import sinon from "sinon"
import { mount, shallow } from "enzyme"
import { assert } from "chai"
import { Provider } from "react-redux"
import configureTestStore from "redux-asserts"

import { AnalyticsDialog, ConnectedAnalyticsDialog } from "./AnalyticsDialog"

import rootReducer from "../../reducers"
import { makeCollection } from "../../factories/collection"
import { makeVideo } from "../../factories/video"

describe("AnalyticsDialog", () => {
  let sandbox, hideDialogStub, video, collection

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    hideDialogStub = sandbox.stub()
    collection = makeCollection("someCollectionKey")
    video = collection.videos[0]
    sandbox.stub(AnalyticsDialog.prototype, "dispatchVideoAnalyticsGet")
    sandbox.stub(AnalyticsDialog.prototype, "dispatchVideoAnalyticsClear")
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = (props = {}, renderFn = shallow) => {
    return renderFn(
      <AnalyticsDialog open={true} hideDialog={hideDialogStub} {...props} />
    )
  }

  describe("mapStateToProps", () => {
    let store

    beforeEach(() => {
      // Setup default store.
      store = configureTestStore(rootReducer)
    })

    const renderComponentInProvider = (props = {}) => {
      return mount(
        <Provider store={store}>
          <ConnectedAnalyticsDialog
            open={true}
            hideDialog={hideDialogStub}
            {...props}
          />
        </Provider>
      )
    }

    it("uses video provided as a prop", () => {
      const wrapper = renderComponentInProvider({ video })
      assert.equal(wrapper.find("AnalyticsDialog").prop("video"), video)
    })

    it("gets video from collection via videoKey if video not provided", () => {
      const initialState = { collectionUi: { selectedVideoKey: video.key } }
      // $FlowFixMe
      store = configureTestStore(rootReducer, initialState)
      const wrapper = renderComponentInProvider({ collection })
      assert.equal(wrapper.find("AnalyticsDialog").prop("video"), video)
    })

    it("prefers a video provided via props over a video in a collection", () => {
      const initialState = { collectionUi: { selectedVideoKey: video.key } }
      // $FlowFixMe
      store = configureTestStore(rootReducer, initialState)
      const otherVideo = makeVideo("someOtherVideoKey")
      const wrapper = renderComponentInProvider({
        video:      otherVideo,
        collection: collection
      })
      const dialogProps = wrapper.find("AnalyticsDialog").props()
      assert.deepEqual(dialogProps.video, otherVideo)
    })

    describe("analyticsNeedsUpdate", () => {
      [
        [{ loaded: false, processing: false, data: false }, true],
        [{ loaded: false, processing: false, data: true }, true],
        [{ loaded: false, processing: true, data: false }, false],
        [{ loaded: false, processing: true, data: true }, false],
        [{ loaded: true, processing: false, data: false }, true],
        [{ loaded: true, processing: false, data: true }, false],
        [{ loaded: true, processing: true, data: false }, true],
        [{ loaded: true, processing: true, data: true }, false]
      ].forEach(testDef => {
        const [params, expectedAnalyticsNeedsUpdate] = testDef
        it(
          `sets analyticsNeedsUpdate to ${String(
            expectedAnalyticsNeedsUpdate
          )}` + ` when params are: ${JSON.stringify(params)}`,
          () => {
            const initialState = {
              videoAnalytics: {
                ...params,
                data: params.data ? new Map([[video.key, {}]]) : {}
              }
            }
            // $FlowFixMe
            store = configureTestStore(rootReducer, initialState)
            const wrapper = renderComponentInProvider({ video })
            assert.equal(
              wrapper.find("AnalyticsDialog").prop("analyticsNeedsUpdate"),
              expectedAnalyticsNeedsUpdate
            )
          }
        )
      })
    })
  })

  describe("when analyticsNeedsUpdate is true", () => {
    [
      [{ open: true, error: false }, { shouldDispatch: true }],
      [{ open: false, error: false }, { shouldDispatch: false }],
      [{ open: true, error: true }, { shouldDispatch: false }],
      [{ open: false, error: true }, { shouldDispatch: false }]
    ].forEach(testDef => {
      const [params, expectations] = testDef
      it(
        `should fulfill expectations: ${JSON.stringify(expectations)}` +
          ` when params are: ${JSON.stringify(params)}`,
        () => {
          const wrapper = renderComponent(
            {
              video,
              analyticsNeedsUpdate: true,
              open:                 params.open,
              error:                params.error
            },
            mount
          )
          const dialogComponent = wrapper.find("AnalyticsDialog").instance()
          assert.equal(
            dialogComponent.dispatchVideoAnalyticsGet.called,
            expectations.shouldDispatch
          )
        }
      )
    })
  })

  describe("body", () => {
    describe("when error", () => {
      const renderWithError = (props = {}) => {
        return renderComponent({
          video,
          error: { some: "error" },
          ...props
        })
      }

      it("renders error message", () => {
        const wrapper = renderWithError()
        assert.equal(wrapper.find(".analytics-dialog-error-ui").length, 1)
      })

      it("'try again' button triggers clear request", () => {
        const wrapper = renderWithError()
        assert.equal(
          AnalyticsDialog.prototype.dispatchVideoAnalyticsClear.called,
          false
        )
        wrapper
          .find(".analytics-dialog-error-ui .try-again-button")
          .simulate("click")
        assert.equal(
          AnalyticsDialog.prototype.dispatchVideoAnalyticsClear.called,
          true
        )
      })
    })

    describe("when not error", () => {
      describe("when processing", () => {
        it("renders LoadingIndicator", () => {
          const wrapper = renderComponent({
            video,
            processing: true
          })
          assert.equal(wrapper.find("LoadingIndicator").length, 1)
          assert.equal(wrapper.find("AnalyticsPane").length, 0)
        })
      })

      describe("when not processing", () => {
        it("renders AnalyticsPane with analytics data", () => {
          const analyticsForVideo = "someanalytics"
          const wrapper = renderComponent({
            video,
            analyticsForVideo
          })
          assert.equal(wrapper.find("LoadingIndicator").length, 0)
          assert.equal(wrapper.find("AnalyticsPane").length, 1)
          assert.equal(
            wrapper.find("AnalyticsPane").prop("analyticsData"),
            analyticsForVideo
          )
        })
      })
    })
  })
})
