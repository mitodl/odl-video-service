// @flow
import { assert } from "chai"

import { makeVideo } from "../factories/video"
import { makeCollectionUrl, makeEmbedUrl } from "./urls"

describe("url library functions", () => {
  it("makeCollectionUrl", () => {
    const video = makeVideo()
    assert.equal(
      makeCollectionUrl(video.collection_key),
      `/collections/${video.collection_key}/`
    )
  })

  it("makeEmbedUrl", () => {
    const video = makeVideo()
    assert.equal(makeEmbedUrl(video.key), `/videos/${video.key}/embed/`)
  })
})
