// @flow
/* global SETTINGS: false */
import { assert } from "chai"
import sinon from "sinon"
import _ from "lodash"
import { PATCH, POST } from "redux-hammock/constants"
import * as fetchFuncs from "redux-hammock/django_csrf_fetch"

import { makeCollection } from "../factories/collection"
import { makeVideo, makeVideoSubtitle } from "../factories/video"
import {
  createCollection,
  getCollections,
  getCollection,
  getVideo,
  updateVideo,
  uploadVideo,
  createSubtitle,
  deleteSubtitle,
  getVideoAnalytics
} from "../lib/api"

describe("api", () => {
  let sandbox, fetchStub

  beforeEach(() => {
    sandbox = sinon.createSandbox()
    fetchStub = sandbox.stub(fetchFuncs, "fetchJSONWithCSRF")
  })

  afterEach(() => {
    sandbox.restore()
  })

  describe("getCollections", () => {
    it("gets collection list", async () => {
      const collections = _.times(2, () => makeCollection())
      fetchStub.returns(Promise.resolve({ results: collections }))

      const result = await getCollections()
      sinon.assert.calledWith(fetchStub, `/api/v0/collections/`)
      assert.deepEqual(result.results, collections)
    })

    it("sends pagination parameters", async () => {
      const paginationParams = { page: 2 }
      await getCollections({ pagination: paginationParams })
      sinon.assert.calledWith(fetchStub, `/api/v0/collections/?page=2`)
    })
  })

  it("creates a new collection", async () => {
    const newCollection = makeCollection()
    fetchStub.returns(Promise.resolve(newCollection))

    const result = await createCollection(newCollection)
    sinon.assert.calledWith(fetchStub, `/api/v0/collections/`, {
      method: "POST",
      body:   JSON.stringify(newCollection)
    })
    assert.deepEqual(result, newCollection)
  })

  it("gets collection detail", async () => {
    const collection = makeCollection()
    fetchStub.returns(Promise.resolve(collection))

    const result = await getCollection(collection.key)
    sinon.assert.calledWith(fetchStub, `/api/v0/collections/${collection.key}/`)
    assert.deepEqual(result, collection)
  })

  it("gets video details", async () => {
    const video = makeVideo()
    fetchStub.returns(Promise.resolve(video))

    const result = await getVideo(video.key)
    sinon.assert.calledWith(fetchStub, `/api/v0/videos/${video.key}/`)
    assert.deepEqual(result, video)
  })

  it("updates video details", async () => {
    const video = makeVideo()
    fetchStub.returns(Promise.resolve(video))

    const payload = {
      title:       "new title",
      description: "new description"
    }
    const result = await updateVideo(video.key, payload)
    sinon.assert.calledWith(fetchStub, `/api/v0/videos/${video.key}/`, {
      method: PATCH,
      body:   JSON.stringify(payload)
    })
    assert.deepEqual(result, video)
  })

  it("can upload videos to a collection", async () => {
    const collectionKey = "test-key",
      mockFiles = [{ name: "file1" }, { name: "file2" }]
    const payload = {
      collection: collectionKey,
      files:      mockFiles
    }
    fetchStub.returns(Promise.resolve({}))

    await uploadVideo(collectionKey, mockFiles)
    sinon.assert.calledWith(fetchStub, `/api/v0/upload_videos/`, {
      method: POST,
      body:   JSON.stringify(payload)
    })
  })

  it("can upload a video subtitle", async () => {
    const fetchFormStub = sandbox.stub(fetchFuncs, "fetchWithCSRF")
    const collectionKey = "test-key"
    const videoKey = "test-key"
    const payload = new FormData()
    // $FlowFixMe
    payload.append("file", [{ name: "file1", data: "" }])
    payload.append("collection", collectionKey)
    payload.append("video", videoKey)
    payload.append("language", "en")
    fetchStub.returns(Promise.resolve({}))

    await createSubtitle(payload)
    sinon.assert.calledWith(fetchFormStub, `/api/v0/upload_subtitles/`, {
      method:  POST,
      body:    payload,
      headers: { Accept: "application/json" }
    })
  })

  it("can delete a video subtitle", async () => {
    const subtitle = makeVideoSubtitle()
    fetchStub.returns(Promise.resolve(subtitle))

    await deleteSubtitle(subtitle.id)
    sinon.assert.calledWith(fetchStub, `/api/v0/subtitles/${subtitle.id}/`, {
      method: "DELETE"
    })
  })

  it("gets video analytics", async () => {
    const video = makeVideo()
    const mockAnalyticsData = { data: { some: "data" } }
    fetchStub.returns(Promise.resolve(mockAnalyticsData))

    const result = await getVideoAnalytics(video.key)
    sinon.assert.calledWith(fetchStub, `/api/v0/videos/${video.key}/analytics/`)
    const expectedResult = {
      key:  video.key,
      data: mockAnalyticsData.data
    }
    assert.deepEqual(result, expectedResult)
  })
})
