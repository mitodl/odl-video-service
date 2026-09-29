import React from "react"
import _ from "lodash"
import sinon from "sinon"
import type { SinonSandbox, SinonStub } from "sinon"
import { render } from "@testing-library/react"
import { assert } from "chai"
import { makeVideo } from "../factories/video"
import type { Video } from "../types/videoTypes"

import VideoList from "./VideoList"

describe("VideoList", () => {
  let sandbox: SinonSandbox, props: React.ComponentProps<typeof VideoList>

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    props = {
      videos:                [...Array(3).keys()].map(() => makeVideo()),
      isAdmin:               true,
      showDeleteVideoDialog: sandbox.stub(),
      showEditVideoDialog:   sandbox.stub(),
      showShareVideoDialog:  sandbox.stub(),
      showVideoMenu:         sandbox.stub(),
      hideVideoMenu:         sandbox.stub(),
      isVideoMenuOpen:       sandbox.stub()
    }
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderComponent = (
    overrides: Partial<React.ComponentProps<typeof VideoList>> = {}
  ) => {
    return render(<VideoList {...props} {...overrides} />)
  }

  describe("render", () => {
    it("renders a VideoCard for each video", () => {
      // Real full mount, no stubbing of renderVideoCard: the original
      // Enzyme test stubbed it out and read back React `key`s via
      // `shallow`, an implementation-detail delegation fact (React keys
      // aren't serialized to the DOM, so no RTL equivalent exists -- Rule
      // 26 DOM capture of a real mount confirmed the rendered markup
      // carries titles instead). Asserting one VideoCard title per video,
      // in order, is the user-visible outcome that delegation fact stood
      // in for, and is safe: VideoCard_test.js already mounts real
      // VideoCard trees (MDC Menu + DropboxChooser) with no stderr, and
      // `makeVideo()` defaults to VIDEO_STATUS_COMPLETE so
      // videoIsProcessing/videoHasError are false without stubbing
      // `../lib/video`.
      const { container } = renderComponent()
      const titleLinks = container.querySelectorAll(".video-card-body h2 a")
      assert.equal(titleLinks.length, props.videos.length)
      assert.deepEqual(
        Array.from(titleLinks).map(link => link.textContent),
        props.videos.map(video => video.title)
      )
    })
  })

  describe("renderVideoCard", () => {
    let video: Video,
      videoList: VideoList,
      videoCard: React.ReactElement<{ isMenuOpen: boolean }>

    // VideoList's Props types isVideoMenuOpen as a plain predicate, which is
    // what the component sees. The test stubs it and then reads sinon's own
    // returnValues off the stub, so the stub view is named separately rather
    // than widening the component's prop type.
    const menuStub = () => props.isVideoMenuOpen as unknown as SinonStub

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
        isAdmin: videoList.props.isAdmin
      }
      assert.deepEqual(
        _.pick(videoCard.props, Object.keys(expectedBasicProps)),
        expectedBasicProps
      )
    })

    it("sets isMenuOpen", () => {
      sinon.assert.calledWith(menuStub(), video.key)
      assert.equal(videoCard.props.isMenuOpen, menuStub().returnValues[0])
    })

    describe("function props", () => {
      const propNames = [
        "showDeleteVideoDialog",
        "showEditVideoDialog",
        "showShareVideoDialog",
        "showVideoMenu",
        "hideVideoMenu"
      ]
      _.forEach(propNames, propName => {
        it(`sets ${propName}`, () => {
          sinon.assert.notCalled(videoList.props[propName])
          videoCard.props[propName]()
          sinon.assert.calledWith(videoList.props[propName], video.key)
        })
      })
    })
  })
})
