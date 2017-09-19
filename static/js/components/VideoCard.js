// @flow
/* global SETTINGS: false */
import React from 'react';

import Card from "./material/Card";
import { makeVideoThumbnailUrl, makeVideoUrl } from "../lib/urls";
import { videoIsProcessing, videoHasError } from "../lib/video";

import type { Video } from "../flow/videoTypes";

type VideoCardProps = {
  video: Video,
  isAdmin: boolean,
  showEditDialog: Function,
  showShareDialog: Function
}

const VideoCard = (props: VideoCardProps) => {
  let videoDisplay,
    headerClass,
    title,
    isProcessing = videoIsProcessing(props.video),
    hasError = videoHasError(props.video);
  headerClass = (isProcessing || hasError) ? 'message' : 'thumbnail';
  title = hasError
    ? props.video.title
    : <a href={makeVideoUrl(props.video.key)}>{props.video.title}</a>;

  if (isProcessing) {
    videoDisplay = <div>
      <h5>In Progress...</h5>
      <p>You should receive an email when the video is ready.</p>
    </div>;
  } else if (hasError) {
    videoDisplay = <div className="error">
      <h5>Upload failed.</h5>
      <p>
        Please <a href={`mailto:${SETTINGS.support_email_address}`}>contact</a> the
        ODL Video Services team.
      </p>
    </div>;
  } else {
    videoDisplay = <a href={makeVideoUrl(props.video.key)}>
      <img src={makeVideoThumbnailUrl(props.video)} />
    </a>;
  }

  return <Card className="video-card">
    <div className={headerClass}>
      { videoDisplay }
    </div>
    <div className="video-card-body">
      <h4 className="mdc-typography--subheading2">
        { title }
      </h4>
    </div>
    <div className="actions">
      {
        props.isAdmin &&
        <a className="material-icons edit-link" onClick={props.showEditDialog}>mode_edit</a>
      }
      {
        !hasError &&
        <a className="material-icons share-link" onClick={props.showShareDialog}>share</a>
      }
    </div>
  </Card>;
};

export default VideoCard;
