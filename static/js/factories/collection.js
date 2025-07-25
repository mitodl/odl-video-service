// @flow
import casual from "casual-browserify"

import { makeVideos } from "./video"

import type { Collection } from "../flow/collectionTypes"

export const makeCollection = (
  collectionKey: string = casual.uuid
): Collection => ({
  key:                 collectionKey,
  created_at:          casual.moment.format(),
  title:               casual.text,
  description:         casual.text,
  videos:              makeVideos(2),
  video_count:         2,
  view_lists:          casual.array_of_words(2),
  admin_lists:         casual.array_of_words(2),
  is_logged_in_only:   false,
  edx_course_id:       casual.word,
  is_admin:            true,
  is_edx_course_admin: true,
  owner:               casual.integer(1, 100),
  owner_info:          {
    id:       casual.integer(1, 100),
    username: casual.username,
    email:    casual.email
  }
})
