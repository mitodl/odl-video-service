import React from "react"
import { connect } from "react-redux"
import type { Dispatch } from "redux"

import Dialog from "../material/Dialog"
import Textfield from "../material/Textfield"
import Textarea from "../material/Textarea"

import { makeEmbedUrl, makeVideoUrl } from "../../lib/urls"
import { formatSecondsToMinutes } from "../../util/util"
import Checkbox from "../material/Checkbox"
import { actions } from "../../actions"
import type { Collection } from "../../types/collectionTypes"
import type { ActionCreator } from "../../types/reduxTypes"
import type { RootState } from "../../types/rootState"
import type { Video, VideoUiState } from "../../types/videoTypes"

type DialogProps = {
  dispatch: Dispatch
  videoUi: VideoUiState
  open: boolean
  hideDialog: () => void
  videoKey: string
  cloudfrontUrl: string
}

class ShareVideoDialog extends React.Component<DialogProps> {
  onChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { dispatch } = this.props
    // `actions` is declared `Record<string, unknown>` in actions/index.ts, so
    // each slice comes back as `unknown`. The cast is erased at runtime -- the
    // call stays a property access on `actions.videoUi`, which is what
    // ShareVideoDialog_test.js drives through the real reducer -- and only
    // tells tsc the shape actions/videoUi.ts already exports.
    dispatch(
      (
        actions.videoUi as { setShareVideoTimeEnabled: ActionCreator }
      ).setShareVideoTimeEnabled(event.target.checked)
    )
  }

  render() {
    const { open, hideDialog, videoKey, videoUi, cloudfrontUrl } = this.props
    const { shareVideoForm } = videoUi
    const startTime = videoUi.videoTime
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
          {cloudfrontUrl ? (
            <Textfield
              readOnly
              label="Open edX video URL"
              id="video-openedx-url"
              value={cloudfrontUrl}
            />
          ) : null}
          <Textarea
            readOnly
            label="Embed HTML"
            id="video-embed-code"
            // {4} not "4": React's own TextareaHTMLAttributes types rows as a
            // number, and it renders rows="4" in the DOM from either form, so
            // this is inert. Widening the prop to string would have made
            // Textarea disagree with React instead.
            rows={4}
            value={`<iframe src="${videoEmbedUrl}" width="560" height="315" frameborder="0" allow="autoplay" allowfullscreen></iframe>`}
          />
          <Checkbox
            label={`Start at ${formatSecondsToMinutes(startTime)}`}
            id="start-checkbox"
            // FOLLOW-UP: this is Checkbox's only call site and it passes no
            // checkGroupName, so the rendered htmlFor is
            // "undefined-start-checkbox" -- the label is not associated with
            // the input. A real accessibility bug, pre-existing, and left
            // alone here because a type migration must not change behaviour.
            value={startTime}
            onChange={this.onChange}
            className="wideLabel"
          />
        </div>
      </Dialog>
    )
  }
}

type OwnProps = {
  collection?: Collection
  video?: Video | null
}

const mapStateToProps = (state: RootState, ownProps: OwnProps) => {
  const {
    videoUi,
    collectionUi: { selectedVideoKey }
  } = state
  let { video } = ownProps

  // The dialog needs a video key passed in as a prop. Depending on the container that includes this dialog,
  // that video key can be retrieved in a couple different ways.
  if (!video && ownProps.collection) {
    video = ownProps.collection.videos.find(obj => obj.key === selectedVideoKey)
  }
  const videoKey = video ? video.key : selectedVideoKey

  return {
    videoUi:       videoUi,
    videoKey:      videoKey,
    cloudfrontUrl: video ? video.cloudfront_url : ""
  }
}

export default connect(mapStateToProps)(ShareVideoDialog)
