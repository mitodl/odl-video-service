// @flow
import React from "react"
import { connect } from "react-redux"
import type { Dispatch } from "redux"

import Dialog from "../material/Dialog"
import Textfield from "../material/Textfield"
import Textarea from "../material/Textarea"

import { makeEmbedUrl } from "../../lib/urls"

type DialogProps = {
  dispatch: Dispatch,
  open: boolean,
  hideDialog: Function,
  videoKey: string
}

class ShareVideoDialog extends React.Component {
  props: DialogProps

  render() {
    const { open, hideDialog, videoKey } = this.props

    const videoShareUrl = `${window.location.origin}${makeEmbedUrl(videoKey)}`

    return (
      <Dialog
        title="Share this Video"
        id="share-video-dialog"
        cancelText="Close"
        open={open}
        hideDialog={hideDialog}
        noSubmit={true}
      >
        <div className="mdc-form-field mdc-form-field--align-end">
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
            value={`<iframe src="${videoShareUrl}" width="560" height="315" frameborder="0" allowfullscreen></iframe>`}
          />
        </div>
      </Dialog>
    )
  }
}

const mapStateToProps = (state, ownProps) => {
  const { collectionUi: { selectedVideoKey } } = state
  const { video } = ownProps

  // The dialog needs a video key passed in as a prop. Depending on the container that includes this dialog,
  // that video key can be retrieved in a couple different ways.
  const videoKey = video ? video.key : selectedVideoKey

  return { videoKey }
}

export default connect(mapStateToProps)(ShareVideoDialog)
