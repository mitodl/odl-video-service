// @flow
/* global SETTINGS */
import { assert } from "chai"
import sinon from "sinon"
import {
  getHLSEncodedUrl,
  videoIsProcessing,
  videoHasError,
  saveToDropbox
} from "./video"
import { makeVideo } from "../factories/video"
import { makeVideoFileName } from "./urls"
import {
  VIDEO_STATUS_CREATED,
  VIDEO_STATUS_UPLOADING,
  VIDEO_STATUS_UPLOAD_FAILED,
  VIDEO_STATUS_TRANSCODING,
  VIDEO_STATUS_TRANSCODE_FAILED_INTERNAL,
  VIDEO_STATUS_TRANSCODE_FAILED_VIDEO,
  VIDEO_STATUS_COMPLETE,
  VIDEO_STATUS_ERROR,
  ENCODING_HLS
} from "../constants"

describe("video library functions", () => {
  let video

  beforeEach(() => {
    video = makeVideo()
  })

  describe("getHLSEncodedUrl", () => {
    it("finds an HLS encoded video", () => {
      assert.equal(
        getHLSEncodedUrl(video),
        // $FlowFixMe: Flow thinks this is undefined. Go home Flow, you're drunk, this is a test.
        video.videofile_set.find(
          videofile => videofile.encoding === ENCODING_HLS
        ).cloudfront_url
      )
    })

    it("returns null if there is not an HLS encoded video", () => {
      video.videofile_set.forEach(file => {
        file.encoding = "original"
      })
      assert.isNull(getHLSEncodedUrl(video))
    })
  })

  describe("videoIsProcessing", () => {
    [
      [VIDEO_STATUS_CREATED, true],
      [VIDEO_STATUS_UPLOADING, true],
      [VIDEO_STATUS_UPLOAD_FAILED, false],
      [VIDEO_STATUS_TRANSCODING, true],
      [VIDEO_STATUS_TRANSCODE_FAILED_INTERNAL, false],
      [VIDEO_STATUS_TRANSCODE_FAILED_VIDEO, false],
      [VIDEO_STATUS_COMPLETE, false],
      [VIDEO_STATUS_ERROR, false]
    ].forEach(([status, bool]) => {
      it(`should return ${String(bool)} for ${status}`, () => {
        video.status = status
        assert.equal(videoIsProcessing(video), bool)
      })
    })
  })

  describe("videoHasError", () => {
    [
      [VIDEO_STATUS_CREATED, false],
      [VIDEO_STATUS_UPLOADING, false],
      [VIDEO_STATUS_UPLOAD_FAILED, true],
      [VIDEO_STATUS_TRANSCODING, false],
      [VIDEO_STATUS_TRANSCODE_FAILED_INTERNAL, true],
      [VIDEO_STATUS_TRANSCODE_FAILED_VIDEO, true],
      [VIDEO_STATUS_COMPLETE, false],
      [VIDEO_STATUS_ERROR, true]
    ].forEach(([status, bool]) => {
      it(`should return ${String(bool)} for ${status}`, () => {
        video.status = status
        assert.equal(videoHasError(video), bool)
      })
    })
  })

  describe("uploadToDropbox", () => {
    it("calls the Dropbox API with correct arguments", () => {
      SETTINGS.cloudfront_base_url = "http://asdasldk.cloudfront.net/"
      const sandbox = sinon.sandbox.create()
      window.Dropbox = { save: () => {} }
      const dropboxStub = sandbox.stub(window.Dropbox, "save")
      saveToDropbox(video)
      sinon.assert.calledWith(
        dropboxStub,
        `${SETTINGS.cloudfront_base_url}${video.key}/video.mp4`,
        makeVideoFileName(video, "mp4")
      )
    })
  })
})
