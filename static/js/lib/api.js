// @flow
import _ from 'lodash'
import {
  fetchJSONWithCSRF,
  fetchWithCSRF
} from "redux-hammock/django_csrf_fetch"
import type { Collection } from "../flow/collectionTypes"

export type VideoUpdatePayload = {
  description?: string
}

export function getCollections(opts = {}) {
  const { pagination } = opts
  console.log("pp: ", pagination)
  let url = "/api/v0/collections/"
  if (pagination) {
    const queryParamsStr = _.map(pagination, (v, k) => {
      return [k, v].map(encodeURIComponent).join('=')
    }).join('&')
    url += `?${queryParamsStr}`
  }
  return fetchJSONWithCSRF(url)
}

export function getCollection(collectionKey: string) {
  return fetchJSONWithCSRF(`/api/v0/collections/${encodeURI(collectionKey)}/`)
}

export function updateCollection(collectionKey: string, payload: Object) {
  return fetchJSONWithCSRF(`/api/v0/collections/${encodeURI(collectionKey)}/`, {
    method: "PATCH",
    body:   JSON.stringify(payload)
  })
}

export function createCollection(payload: Collection) {
  return fetchJSONWithCSRF(`/api/v0/collections/`, {
    method: "POST",
    body:   JSON.stringify(payload)
  })
}

export function getVideo(videoKey: string) {
  return fetchJSONWithCSRF(`/api/v0/videos/${encodeURI(videoKey)}/`)
}

export function updateVideo(videoKey: string, payload: VideoUpdatePayload) {
  return fetchJSONWithCSRF(`/api/v0/videos/${encodeURI(videoKey)}/`, {
    method: "PATCH",
    body:   JSON.stringify(payload)
  })
}

export function deleteVideo(videoKey: string) {
  return fetchJSONWithCSRF(`/api/v0/videos/${videoKey}/`, {
    method: "DELETE"
  })
}

export function uploadVideo(collectionKey: string, files: Array<Object>) {
  return fetchJSONWithCSRF(`/api/v0/upload_videos/`, {
    method: "POST",
    body:   JSON.stringify({ collection: collectionKey, files: files })
  })
}

export function createSubtitle(payload: FormData) {
  return fetchWithCSRF(`/api/v0/upload_subtitles/`, {
    headers: {
      Accept: "application/json"
    },
    method: "POST",
    body:   payload
  })
}

export function deleteSubtitle(videoSubtitleKey: number) {
  return fetchJSONWithCSRF(`/api/v0/subtitles/${videoSubtitleKey}/`, {
    method: "DELETE"
  })
}

export async function getVideoAnalytics(videoKey: string) {
  if (window && window.ovsMockAnalyticsData) {
    return Promise.resolve({
      key:  videoKey,
      data: window.ovsMockAnalyticsData
    })
  }
  let url = `/api/v0/videos/${videoKey}/analytics/`
  if (window && window.ovsMockAnalyticsError) {
    url += `?throw=1`
  } else if (window && window.ovsMockAnalytics) {
    url += `?mock=1&seed=${videoKey}`
  }
  const response = await fetchJSONWithCSRF(url)
  return {
    key:  videoKey,
    data: response.data
  }
}
