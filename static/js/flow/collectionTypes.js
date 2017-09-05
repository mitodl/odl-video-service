// @flow

import type { Video } from './videoTypes';

export type Collection = {
  key:                string,
  title:              string,
  description:        ?string,
  owner:              number,
  videos:             Array<Video>,
  view_lists:         Array<string>,
  admin_lists:        Array<string>,
  created_at:         string
};
