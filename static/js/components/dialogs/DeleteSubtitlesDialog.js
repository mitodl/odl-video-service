// @flow
import React from "react"
import _ from "lodash"
import { connect } from "react-redux"
import type { Dispatch } from "redux"

import Dialog from "../material/Dialog"

import { actions } from "../../actions"

import type { VideoSubtitle } from "../../flow/videoTypes"

export class DeleteSubtitlesDialog extends React.Component<*, void> {
  props: {
    dispatch: Dispatch,
    open: boolean,
    hideDialog: Function,
    subtitlesFile: VideoSubtitle,
    videoKey: string
  }

  render() {
    const { open, hideDialog, subtitlesFile } = this.props
    if (!subtitlesFile) {
      return null
    }

    return (
      <Dialog
        title="Delete Subtitles"
        id="delete-subtitles-dialog"
        cancelText="Cancel"
        submitText="Yes, Delete"
        open={open}
        hideDialog={hideDialog}
        onAccept={this.onConfirmDeletion}
      >
        <div className="delete-subtitles-dialog">
          <span>Are you sure you want to delete this subtitles file?</span>
          <h5>{subtitlesFile.filename}</h5>
        </div>
      </Dialog>
    )
  }

  onConfirmDeletion = async () => {
    await this.deleteSubtitlesFile()
    this.addToastMessage()
    this.updateVideo()
  }

  deleteSubtitlesFile = async () => {
    const { dispatch, subtitlesFile } = this.props
    await dispatch(actions.videoSubtitles.delete(subtitlesFile.id))
  }

  addToastMessage = () => {
    this.props.dispatch(
      actions.toast.addMessage({
        message: {
          key:     "subtitles-deleted",
          content: "Subtitles file deleted",
          icon:    "check"
        }
      })
    )
  }

  updateVideo = () => {
    this.props.dispatch(actions.videos.get(this.props.videoKey))
  }
}

export const mapStateToProps = (state: Object) => {
  const { videoUi, videos } = state
  const { currentVideoKey, currentSubtitlesKey } = videoUi
  const video = videos.data.get(currentVideoKey)
  let subtitlesFile = null
  if (video) {
    subtitlesFile = _.find(video.videosubtitle_set, { id: currentSubtitlesKey })
  }
  return { subtitlesFile, videoKey: currentVideoKey }
}

const ConnectedDeleteSubtitlesDialog = connect(mapStateToProps)(
  DeleteSubtitlesDialog
)

export default ConnectedDeleteSubtitlesDialog
