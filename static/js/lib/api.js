// @flow
import { fetchJSONWithCSRF } from 'redux-hammock/django_csrf_fetch';

export function getCollections() {
  return fetchJSONWithCSRF(`/api/v0/collections/`);
}

export function getCollection(collectionKey: string) {
  return fetchJSONWithCSRF(`/api/v0/collections/${encodeURI(collectionKey)}/`);
}

export function updateCollection(collectionKey: string, payload: Object) {
  return fetchJSONWithCSRF(`/api/v0/collections/${encodeURI(collectionKey)}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

// import to allow mocking in tests
export function getVideo(videoKey: string) {
  return fetchJSONWithCSRF(`/api/v0/videos/${encodeURI(videoKey)}/`);
}

export type VideoUpdatePayload = {
  description?: string,
};

export function updateVideo(videoKey: string, payload: VideoUpdatePayload) {
  return fetchJSONWithCSRF(`/api/v0/videos/${encodeURI(videoKey)}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}
