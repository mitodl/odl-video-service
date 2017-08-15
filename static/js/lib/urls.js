// @flow

export const makeEmbedUrl = (videoKey: string) => `/videos/${encodeURI(videoKey)}/embed/`;
export const makeCollectionUrl = (collectionKey: string) => `/collections/${encodeURI(collectionKey)}/`;
