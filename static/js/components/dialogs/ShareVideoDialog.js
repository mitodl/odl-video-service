// @flow
import React from "react"
import { connect } from "react-redux"
import type { Dispatch } from "redux"

import Dialog from "../material/Dialog"
import Textfield from "../material/Textfield"
import Textarea from "../material/Textarea"

import { makeEmbedUrl, makeVideoUrl } from "../../lib/urls"
import { formatSecondsToMinutes } from "../../util/util"
import Checkbox from "../material/Checkbox"
import * as videoActions from "../../actions/videoUi"
import type { VideoUiState } from "../../flow/videoTypes"

type DialogProps = {
  dispatch: Dispatch,
  videoUi: VideoUiState,
  open: boolean,
  hideDialog: Function,
  videoKey: string
}

class ShareVideoDialog extends React.Component<*, void> {
  props: DialogProps

  onChange = (event: Object) => {
    const { dispatch } = this.props
    dispatch(videoActions.setShareVideoTimeEnabled(event.target.checked))
  }

  render() {
    const {
      open,
      hideDialog,
      videoKey,
      videoUi: { shareVideoForm }
    } = this.props
    const startTime = shareVideoForm.videoTime
    const startParam = shareVideoForm.shareTime ? `?start=${startTime}` : ""
    const videoShareUrl = `${window.location.origin}${makeVideoUrl(
      videoKey
    )}${startParam}`
    const videoEmbedUrl = `${window.location.origin}${makeEmbedUrl(
      videoKey
    )}${startParam}`
    return (
      <Dialog
        title="Share this Video"
        id="share-video-dialog"
        cancelText="Close"
        open={open}
        hideDialog={hideDialog}
        noSubmit={true}
      >
        <div className="ovs-form-dialog">
          <Textfield
            readOnly
            label="Video URL"
            id="video-url"
            value={videoShareUrl}
          />
          <Textarea
            readOnly
            label="Embed HTML"
            id="video-embed-code"
            rows="4"
            value={`<iframe src="${videoEmbedUrl}" width="560" height="315" frameborder="0" allowfullscreen></iframe>`}
          />
          <Checkbox
            label={`Start at ${formatSecondsToMinutes(startTime)}`}
            id="start-checkbox"
            value={startTime}
            onChange={this.onChange}
            className="wideLabel"
          />
        </div>
      </Dialog>
    )
  }
}

const mapStateToProps = (state, ownProps) => {
  const { videoUi, collectionUi: { selectedVideoKey } } = state
  const { video } = ownProps

  // The dialog needs a video key passed in as a prop. Depending on the container that includes this dialog,
  // that video key can be retrieved in a couple different ways.
  const videoKey = video ? video.key : selectedVideoKey

  return {
    videoUi:  videoUi,
    videoKey: videoKey
  }
}

export default connect(mapStateToProps)(ShareVideoDialog)
