// @flow
/* global SETTINGS: false */
import React from "react"
import { assert } from "chai"
import sinon from "sinon"
import { mount } from "enzyme"

import { actions } from "../actions"

import { mapStateToProps, withVideoAnalytics } from "./withVideoAnalytics"

describe("withVideoAnalytics", () => {
  let sandbox

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
  })

  afterEach(() => {
    sandbox.restore()
  })

  describe("mapStateToProps", () => {
    describe("needsUpdate", () => {
      const testSpecs = [
        [{ video: true, processing: true, loaded: false }, false],
        [{ video: true, processing: true, loaded: true }, false],
        [{ video: true, processing: false, loaded: false }, true],
        [{ video: true, processing: false, loaded: true }, false],
        [{ video: false, processing: true, loaded: false }, false],
        [{ video: false, processing: true, loaded: true }, false],
        [{ video: false, processing: false, loaded: false }, false],
        [{ video: false, processing: false, loaded: true }, false]
      ]
      testSpecs.forEach(testSpec => {
        const [inputs, expected] = testSpec
        it(`is '${JSON.stringify(expected)}' when inputs are '${JSON.stringify(
          inputs
        )}'`, () => {
          const state = {
            videoAnalytics: {
              loaded:     inputs.loaded,
              processing: inputs.processing
            }
          }
          const ownProps = { video: inputs.video }
          const props = mapStateToProps(state, ownProps)
          assert.equal(props.needsUpdate, expected)
        })
      })

      it("passes ownProps.video", () => {
        const state = { videoAnalytics: {} }
        const ownProps = { video: "someVideoObj" }
        const props = mapStateToProps(state, ownProps)
        assert.equal(props.video, ownProps.video)
      })

      it("passes state.videoAnalytics", () => {
        const state = { videoAnalytics: { some: "videoAnalytics" } }
        const props = mapStateToProps(state)
        assert.equal(props.videoAnalytics, state.videoAnalytics)
      })
    })

    describe("WrappedComponent", () => {
      class DummyComponent extends React.Component<*, void> {
        render() {
          return <div>DummyComponent</div>
        }
      }

      const WrappedComponent = withVideoAnalytics(DummyComponent)

      describe("updateIfNeeded", () => {
        let stubs

        beforeEach(() => {
          stubs = {
            update: sandbox.stub(WrappedComponent.prototype, "update")
          }
        })

        describe("when needsUpdate is true", () => {
          it("calls update", () => {
            mount(<WrappedComponent needsUpdate={true} />)
            sinon.assert.called(stubs.update)
          })
        })

        describe("when needsUpdate is false", () => {
          it("does not call update", () => {
            mount(<WrappedComponent needsUpdate={false} />)
            sinon.assert.notCalled(stubs.update)
          })
        })
      })

      describe("update", () => {
        let stubs

        beforeEach(() => {
          stubs = {
            dispatch:          sandbox.spy(),
            videoAnalyticsGet: sandbox.stub(actions.videoAnalytics, "get")
          }
        })

        it("dispatches action with video.key", () => {
          const videoKey = "someVideoKey"
          mount(
            <WrappedComponent
              dispatch={stubs.dispatch}
              needsUpdate={true}
              video={{ key: videoKey }}
            />
          )
          sinon.assert.calledWith(stubs.videoAnalyticsGet, videoKey)
          sinon.assert.calledWith(
            stubs.dispatch,
            stubs.videoAnalyticsGet.returnValues[0]
          )
        })
      })

      describe("generatePropsForWrappedComponent", () => {
        it("passes on expected props", () => {
          const extraProps = {
            someKey:      "someVal",
            someOtherKey: "someOtherVal"
          }
          const video = { some: "video" }
          const videoAnalytics = { some: "videoAnalytics" }
          const wrapper = mount(
            <WrappedComponent
              {...extraProps}
              video={video}
              videoAnalytics={videoAnalytics}
            />
          )
          const wrapped = wrapper.find("DummyComponent")
          assert.deepEqual(wrapped.props(), {
            ...extraProps,
            video,
            videoAnalytics
          })
        })
      })
    })
  })
})
