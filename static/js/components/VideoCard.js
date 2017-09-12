// @flow
import React from 'react';

import Card from "./material/Card";
import { makeVideoThumbnailUrl, makeVideoUrl } from "../lib/urls";

import type { Video } from "../flow/videoTypes";

type VideoCardProps = {
  video: Video,
  isAdmin: boolean,
  showEditDialog: Function,
  showShareDialog: Function
}

const VideoCard = (props: VideoCardProps) => (
  <Card className="video-card">
    <div className="thumbnail">
      <a href={makeVideoUrl(props.video.key)}><img src={makeVideoThumbnailUrl(props.video)} /></a>
    </div>
    <div className="video-card-body">
      <h4 className="mdc-typography--subheading2">
        <a href={makeVideoUrl(props.video.key)}>{props.video.title}</a>
      </h4>
      <div className="actions">
        {
          props.isAdmin &&
          <a className="material-icons edit-link" onClick={props.showEditDialog}>mode_edit</a>
        }
        <a className="material-icons share-link" onClick={props.showShareDialog}>share</a>
      </div>
    </div>
  </Card>
);

export default VideoCard;
