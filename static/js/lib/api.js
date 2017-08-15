// @flow
import { fetchJSONWithCSRF } from 'redux-hammock/django_csrf_fetch';

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
