// @flow

import type { Collection } from "../flow/collectionTypes";
import type { RestState } from "../flow/restTypes";

export const getActiveCollectionDetail =
  (state: { collections?: ?RestState<Collection> }): ?Collection => (
    state.collections && state.collections.data && state.collections.loaded
      ? state.collections.data
      : null
  );
