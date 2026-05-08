// @flow
/* global SETTINGS: false */
import React from "react"
import _ from "lodash"

import Menu from "./material/Menu"
import Card from "./material/Card"
import { makeVideoThumbnailUrl, makeVideoUrl } from "../lib/urls"
import { videoIsProcessing, videoHasError, saveToDropbox } from "../lib/video"
import DropboxChooser from "react-dropbox-chooser"

import type { Video } from "../flow/videoTypes"

type VideoCardProps = {
  video: Video,
  isAdmin: boolean,
  isMenuOpen: boolean,
  showDeleteVideoDialog: Function,
  showEditVideoDialog: Function,
  showShareVideoDialog: Function,
  showVideoMenu: Function,
  hideVideoMenu: Function,
  onReplaceVideo?: Function
}

class VideoCard extends React.Component<VideoCardProps, void> {
  dropboxTriggerRef: ?HTMLElement

  triggerReplaceDropbox() {
    if (this.dropboxTriggerRef) {
      this.dropboxTriggerRef.click()
    }
  }

  render() {
    const { video, isAdmin, isMenuOpen, showShareVideoDialog,
      showEditVideoDialog, showDeleteVideoDialog,
      showVideoMenu, hideVideoMenu, onReplaceVideo } = this.props

    let videoDisplay
    const hasError = videoHasError(video),
      isProcessing = videoIsProcessing(video)
    const headerClass = isProcessing || hasError ? "message" : "thumbnail",
      videoUrl = makeVideoUrl(video.key)

    if (isProcessing) {
      videoDisplay = (
        <div>
          <h5>In Progress...</h5>
          <p>You should receive an email when the video is ready.</p>
        </div>
      )
    } else if (hasError) {
      videoDisplay = (
        <div className="error">
          <h5>Upload failed.</h5>
          <p>
            Please{" "}
            <a href={`mailto:${SETTINGS.support_email_address}`}>contact</a> the
            ODL Video Services team.
          </p>
        </div>
      )
    } else {
      videoDisplay = (
        <a href={videoUrl}>
          <img src={makeVideoThumbnailUrl(video)} alt="" />
        </a>
      )
    }

    let menuItems = [
      { label: "Share", action: showShareVideoDialog.bind(this) }
    ]

    if (isAdmin) {
      menuItems = _.concat(
        menuItems,
        { label: "Edit", action: showEditVideoDialog.bind(this) },
        {
          label:  "Save To Dropbox",
          action: saveToDropbox.bind(this, video)
        },
        {
          label:  "Replace",
          action: this.triggerReplaceDropbox.bind(this)
        },
        { label: "Delete", action: showDeleteVideoDialog.bind(this) }
      )
    }

    return (
      <Card className="video-card">
        <div className={headerClass}>{videoDisplay}</div>
        <div className="video-card-body">
          <h2 className="mdc-typography--subheading2">
            <a href={videoUrl} title={video.title}>
              {video.title}
            </a>
          </h2>
        </div>
        <div className="actions">
          <Menu
            key={video.key}
            showMenu={showVideoMenu}
            closeMenu={hideVideoMenu}
            open={isMenuOpen}
            menuItems={menuItems}
          />
          {isAdmin && onReplaceVideo && (
            <div style={{ display: "none" }}>
              <DropboxChooser
                appKey={SETTINGS.dropbox_key}
                success={files => onReplaceVideo(files[0])}
                linkType="direct"
                multiselect={false}
                extensions={["video"]}
              >
                <button ref={el => {
                  this.dropboxTriggerRef = el
                }}>replace</button>
              </DropboxChooser>
            </div>
          )}
        </div>
      </Card>
    )
  }
}

export default VideoCard
