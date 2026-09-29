import type { RestState } from "./restTypes"
import type {
  Collection,
  CollectionListItem,
  CollectionUiState,
  CollectionsPagination
} from "./collectionTypes"
import type { Video, VideoUiState } from "./videoTypes"
import type { VideoAnalyticsData } from "./videoAnalyticsTypes"
import type { ToastState } from "./toastTypes"
import type { User } from "./userTypes"
import type { DialogVisibilityState } from "../lib/dialog"

/*
 * Mirrors what reducers/index.js hands combineReducers: five hand-written
 * reducers plus one slice per entry in lib/redux_rest's `endpoints`, each
 * derived by redux-hammock's deriveReducers and therefore a RestState.
 *
 * The REST slices' type parameters come from each endpoint's `initialState`
 * rather than from its name -- several store a Map keyed by the record's key,
 * not an array, and getting that backwards is exactly the kind of mistake the
 * old `Record<string, any>` placeholder could not catch.
 */

export type CommonUiState = DialogVisibilityState & {
  drawerOpen: boolean
  menuVisibility: {
    [key: string]: boolean
  }
  FAQVisibility: Map<string, boolean>
}

export type RootState = {
  // hand-written reducers
  collectionsPagination: CollectionsPagination
  commonUi: CommonUiState
  collectionUi: CollectionUiState
  videoUi: VideoUiState
  toast: ToastState

  // derived from lib/redux_rest endpoints
  collectionsList: RestState<Array<CollectionListItem>>
  collections: RestState<Map<string, Collection>>
  uploadVideo: RestState<unknown>
  videos: RestState<Map<string, Video>>
  videoSubtitles: RestState<Map<string, unknown>>
  videoAnalytics: RestState<Map<string, VideoAnalyticsData>>
  syncCollectionEdX: RestState<unknown>
  potentialCollectionOwners: RestState<Array<User>>
}
