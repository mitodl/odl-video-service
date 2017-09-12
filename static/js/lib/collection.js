// @flow
import R from 'ramda';

import type { Collection } from "../flow/collectionTypes";
import type { RestState } from "../flow/restTypes";

export const getActiveCollectionDetail =
  (state: { collections?: ?RestState<Collection> }): ?Collection => (
    state.collections && state.collections.data && state.collections.loaded
      ? state.collections.data
      : null
  );

export const getVideoWithKey = (collection: Collection, key: string) => (
  R.compose(
    R.find(R.propEq('key', key)),
    R.defaultTo([])
  )(collection.videos)
);
