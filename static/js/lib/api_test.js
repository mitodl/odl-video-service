// @flow
/* global SETTINGS: false */
import { assert } from 'chai';
import sinon from 'sinon';
import { PATCH } from 'redux-hammock/constants';
import * as fetchFuncs from "redux-hammock/django_csrf_fetch";

import { makeVideo } from '../factories/video';
import {
  getVideo,
  updateVideo,
} from '../lib/api';

describe('api', () => {
  let sandbox, fetchStub;

  beforeEach(() => {
    sandbox = sinon.sandbox.create();
    fetchStub = sandbox.stub(fetchFuncs, "fetchJSONWithCSRF");
  });

  afterEach(() => {
    sandbox.restore();
  });

  it("gets video details", async () => {
    const video = makeVideo();
    fetchStub.returns(Promise.resolve(video));

    const result = await getVideo(video.key);
    sinon.assert.calledWith(fetchStub, `/api/v0/videos/${video.key}/`);
    assert.deepEqual(result, video);
  });

  it('updates video details', async () => {
    const video = makeVideo();
    fetchStub.returns(Promise.resolve(video));

    const payload = {
      title: "new title"
    };
    const result = await updateVideo(video.key, payload);
    sinon.assert.calledWith(fetchStub, `/api/v0/videos/${video.key}/`, {
      method: PATCH,
      body: JSON.stringify(payload)
    });
    assert.deepEqual(result, video);
  });
});
