// @flow
/* global SETTINGS: false */
import React from 'react';
import _ from 'lodash';

import Menu from "./material/Menu";
import Card from "./material/Card";
import { makeVideoThumbnailUrl, makeVideoUrl } from "../lib/urls";
import { videoIsProcessing, videoHasError, saveToDropbox } from "../lib/video";

import type { Video } from "../flow/videoTypes";

type VideoCardProps = {
  video: Video,
  isAdmin: boolean,
  isMenuOpen: boolean,
  showDeleteDialog: Function,
  showEditDialog: Function,
  showShareDialog: Function,
  showVideoMenu: Function,
  closeVideoMenu: Function
}

const VideoCard = (props: VideoCardProps) => {
  let videoDisplay,
    headerClass,
    videoUrl,
    isProcessing = videoIsProcessing(props.video),
    hasError = videoHasError(props.video);
  headerClass = (isProcessing || hasError) ? 'message' : 'thumbnail';
  videoUrl = makeVideoUrl(props.video.key);

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
    videoDisplay = <a href={videoUrl}>
      <img src={makeVideoThumbnailUrl(props.video)} alt="" />
    </a>;
  }

  let menuItems = [
    {label: 'Share', action: props.showShareDialog.bind(this)}
  ];

  if (props.isAdmin) {
    menuItems = _.concat(menuItems,
      {label: 'Edit', action: props.showEditDialog.bind(this)},
      {label: 'Save To Dropbox', action: saveToDropbox.bind(this, props.video)},
      {label: 'Delete', action: props.showDeleteDialog.bind(this)}
    );
  }

  return <Card className="video-card">
    <div className={headerClass}>
      { videoDisplay }
    </div>
    <div className="video-card-body">
      <h2 className="mdc-typography--subheading2">
        <a href={videoUrl} title={props.video.title}>{props.video.title}</a>
      </h2>
    </div>
    <div className="actions">
      <Menu
        key={props.video.key}
        showMenu={props.showVideoMenu}
        closeMenu={props.closeVideoMenu}
        open={props.isMenuOpen}
        menuItems={menuItems}
      />
    </div>
  </Card>;
};

export default VideoCard;
