// @flow
/* global SETTINGS: false */
import { assert } from 'chai';
import sinon from 'sinon';
import _ from 'lodash';
import { PATCH, POST } from 'redux-hammock/constants';
import * as fetchFuncs from "redux-hammock/django_csrf_fetch";

import { makeCollection } from '../factories/collection';
import { makeVideo } from '../factories/video';
import {
  createCollection,
  getCollections,
  getCollection,
  getVideo,
  updateVideo,
  uploadVideo
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

  it("gets collection list", async () => {
    const collections = _.times(2, () => makeCollection());
    fetchStub.returns(Promise.resolve(collections));

    const result = await getCollections();
    sinon.assert.calledWith(fetchStub, `/api/v0/collections/`);
    assert.deepEqual(result, collections);
  });

  it("creates a new collection", async () => {
    const newCollection = makeCollection();
    fetchStub.returns(Promise.resolve(newCollection));

    const result = await createCollection(newCollection);
    sinon.assert.calledWith(fetchStub, `/api/v0/collections/`, {
      method: 'POST',
      body: JSON.stringify(newCollection)
    });
    assert.deepEqual(result, newCollection);
  });

  it("gets collection detail", async () => {
    const collection = makeCollection();
    fetchStub.returns(Promise.resolve(collection));

    const result = await getCollection(collection.key);
    sinon.assert.calledWith(fetchStub, `/api/v0/collections/${collection.key}/`);
    assert.deepEqual(result, collection);
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

  it("can upload videos to a collection", async () => {
    const collectionKey = 'test-key',
      mockFiles = [{name: 'file1'}, {name: 'file2'}];
    const payload = {
      collection: collectionKey,
      files: mockFiles
    };
    fetchStub.returns(Promise.resolve({}));

    await uploadVideo(collectionKey, mockFiles);
    sinon.assert.calledWith(fetchStub, `/api/v0/upload_videos/`, {
      method: POST,
      body: JSON.stringify(payload)
    });
  });
});
