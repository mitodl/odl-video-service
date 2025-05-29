// @flow
import casual from "casual-browserify"

import type { EdxEndpoint, EdxEndpointList } from "../flow/edxEndpointTypes"


export const makeEdxEndpoint = (): EdxEndpoint => {
  const id = casual.integer(1, 1000)
  return {
    id,
    name:               `EdX Endpoint ${id}`,
    base_url:           `https://edx-endpoint-${id}.example.com`,
    edx_video_api_path: "/api/v0/videos/",
    is_global_default:  casual.boolean,
    created_at:         casual.date(),
    updated_at:         casual.date(),
  }
}

export const makeEdxEndpointList = (count = 3): EdxEndpointList => {
  return [...Array(count).keys()].map(() => makeEdxEndpoint())
}
