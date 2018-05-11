// @flow
import React from "react"
import _ from "lodash"
import sinon from "sinon"
import { shallow } from "enzyme"
import { assert } from "chai"
import { makeVideo } from "../factories/video"

import VideoList from "./VideoList"

describe("VideoList", () => {
  let sandbox, props

  beforeEach(() => {
    sandbox = sinon.sandbox.create()
    props = {
      videos:                [...Array(3).keys()].map(() => makeVideo()),
      isAdmin:               true,
      showDeleteVideoDialog: sandbox.stub(),
      showEditVideoDialog:   sandbox.stub(),
      showShareVideoDialog:  sandbox.stub(),
      showVideoMenu:         sandbox.stub(),
      hideVideoMenu:         sandbox.stub(),
      isVideoMenuOpen:       sandbox.stub(),
    }
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = (overrides = {}) => {
    return shallow(<VideoList {...props} {...overrides} />)
  }

  describe("render", () => {
    it("renders a VideoCard for each video", () => {
      sandbox.stub(VideoList.prototype, 'renderVideoCard').callsFake((video) => {
        return (<div className="mocked-renderVideoCard" key={video.key}></div>)
      })
      const wrapper = renderComponent()
      const videos = wrapper.instance().props.videos
      const videoCards = wrapper.find('.mocked-renderVideoCard')
      assert.equal(videoCards.length, videos.length)
      assert.deepEqual(
        videoCards.map((videoCard) => videoCard.key()),
        videos.map((video) => video.key)
      )
    })
  })

  describe("renderVideoCard", () => {
    let video, videoList, videoCard

    beforeEach(() => {
      video = makeVideo()
      videoList = new VideoList(props)
      videoCard = videoList.renderVideoCard(video)
    })

    it("sets key", () => {
      assert.equal(videoCard.key, video.key)
    })

    it("sets basic props", () => {
      const expectedBasicProps = {
        video,
        isAdmin: videoList.props.isAdmin,
      }
      assert.deepEqual(
        _.pick(videoCard.props, Object.keys(expectedBasicProps)),
        expectedBasicProps
      )
    })

    it("sets isMenuOpen", () => {
      sinon.assert.calledWith(videoList.props.isVideoMenuOpen, video.key)
      assert.equal(
        videoCard.props.isMenuOpen,
        videoList.props.isVideoMenuOpen.returnValues[0]
      )
    })

    describe("function props", () => {
      const propNames = [
        "showDeleteVideoDialog",
        "showEditVideoDialog",
        "showShareVideoDialog",
        "showVideoMenu",
        "hideVideoMenu",
      ]
      _.forEach(propNames, (propName) => {
        it(`sets ${propName}`, () => {
          sinon.assert.notCalled(videoList.props[propName])
          videoCard.props[propName]()
          sinon.assert.calledWith(videoList.props[propName], video.key)
        })
      })
    })
  })
})
