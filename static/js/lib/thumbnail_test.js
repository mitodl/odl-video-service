// @flow
import { assert } from "chai"

import { getThumbnailDimensionError } from "./thumbnail"

describe("thumbnail", () => {
  describe("getThumbnailDimensionError", () => {
    [
      [1280, 720],
      [640, 360],
      [1920, 1080]
    ].forEach(([width, height]) => {
      it(`accepts a ${width}x${height} image`, () => {
        assert.isNull(getThumbnailDimensionError(width, height))
      })
    })
    ;[
      [1280, 615], // wider than 16:9
      [1600, 1200], // 4:3
      [480, 270] // 16:9 but smaller than 640x360
    ].forEach(([width, height]) => {
      it(`rejects a ${width}x${height} image with a message naming the requirement`, () => {
        const error = getThumbnailDimensionError(width, height)
        assert.include(error, "16:9")
        assert.include(error, "640x360")
        assert.include(error, `${width}x${height}`)
      })
    })
  })
})
