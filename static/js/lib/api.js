// @flow
import {
  fetchJSONWithCSRF,
  fetchWithCSRF
} from "redux-hammock/django_csrf_fetch"
import type { Collection } from "../flow/collectionTypes"

export type VideoUpdatePayload = {
  description?: string
}

export function getCollections() {
  return fetchJSONWithCSRF(`/api/v0/collections/`)
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
