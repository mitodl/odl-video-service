import React from "react"
import { assert } from "chai"
import { mount, shallow } from "enzyme"
import sinon from "sinon"

import { makeVideoAnalyticsData } from "../../factories/videoAnalytics"
import { ConditionalLabel, AnalyticsChart } from "./AnalyticsChart"

describe("AnalyticsChartTests", () => {
  let analyticsData, props, sandbox

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    analyticsData = makeVideoAnalyticsData(10)
    props = { analyticsData }
  })

  afterEach(() => {
    sandbox.restore()
  })

  describe("ConditionalLabel", () => {
    const renderLabel = (props) => {
      return shallow(<ConditionalLabel {...props} />)
    }

    it("passes props to testFn", () => {
      const props = {
        testFn: sandbox.stub(),
        some:   "otherValue"
      }
      renderLabel(props)
      assert.isTrue(props.testFn.calledWith(props))
    })

    describe("when testFn returns true", () => {
      it("returns victory label", () => {
        const props = {
          testFn:   sandbox.stub().returns(true),
          someProp: "otherValue"
        }
        const wrapper = renderLabel(props)
        const victoryLabel = wrapper.find("VictoryLabel")
        assert.deepEqual(victoryLabel.prop("someProp"), props.someProp)
      })
    })

    describe("when testFn returns false", () => {
      it("returns null", () => {
        const props = { testFn: sandbox.stub().returns(false) }
        const wrapper = renderLabel(props)
        assert.isTrue(wrapper.get(0) === null)
      })
    })
  })

  describe("AnalyticsChart", () => {

    const renderChart = () => {
      const wrapper = mount(<AnalyticsChart {...props} />)
      wrapper.update()
      return wrapper
    }

    it("renders", () => {
      const wrapper = renderChart()
      assert.isTrue(wrapper.exists())
    })

    describe("when it unmounts", () => {
      it("removes resize handler", () => {
        const wrapper = renderChart()
        const tearDownResizeStub = sandbox.stub(
          wrapper.instance(), '_tearDownResizeHandler')
        assert.isFalse(tearDownResizeStub.called)
        wrapper.unmount()
        assert.isTrue(tearDownResizeStub.called)
      })
    })

    describe("onResize", () => {
      it("calls updateDimensions", () => {
        const wrapper = renderChart()
        const _updateDimensionsStub = sandbox.stub(
          wrapper.instance(), '_updateDimensions')
        assert.isFalse(_updateDimensionsStub.called)
        wrapper.instance().onResize()
        assert.isTrue(_updateDimensionsStub.called)
      })
    })
  })
})
