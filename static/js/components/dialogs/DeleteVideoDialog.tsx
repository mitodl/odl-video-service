import React from "react"
import { connect } from "react-redux"
import type { UnknownAction } from "redux"
import type { ThunkDispatch } from "redux-thunk"

import Dialog from "../material/Dialog"

import { actions } from "../../actions"
import { getVideoWithKey } from "../../lib/collection"
import { makeCollectionUrl } from "../../lib/urls"

import type { Collection } from "../../types/collectionTypes"
import type { RootState } from "../../types/rootState"
import type { Video } from "../../types/videoTypes"

type DialogProps = {
  dispatch: ThunkDispatch<RootState, unknown, UnknownAction>
  open: boolean
  hideDialog: () => void
  shouldUpdateCollection: boolean
  video: Video
  window?: Window
}

export class DeleteVideoDialog extends React.Component<DialogProps> {
  confirmDeletion = async () => {
    const { dispatch, video, shouldUpdateCollection } = this.props
    const window_ = this.props.window || window

    await dispatch(actions.videos.delete(video.key))
    dispatch(
      actions.toast.addMessage({
        message: {
          key:     "video-delete",
          content: `Video "${video.title}" was deleted.`,
          icon:    "check"
        }
      })
    )
    if (shouldUpdateCollection) {
      dispatch(actions.collections.get(video.collection_key))
    } else {
      const collectionUrl = makeCollectionUrl(video.collection_key)
      window_.location = `${window_.location.origin}${collectionUrl}`
    }
  }

  render() {
    const { open, hideDialog, video } = this.props

    if (!video) return null

    return (
      <Dialog
        title="Delete Video"
        id="delete-video-dialog"
        cancelText="Cancel"
        submitText="Yes, Delete"
        open={open}
        hideDialog={hideDialog}
        onAccept={this.confirmDeletion}
      >
        <div className="delete-video-dialog">
          <span>Are you sure you want to delete this video?</span>
          <h5>{video.title}</h5>
        </div>
      </Dialog>
    )
  }
}

type OwnProps = {
  collection?: Collection
  video?: Video
}

export const mapStateToProps = (state: RootState, ownProps: OwnProps) => {
  const {
    collectionUi: { selectedVideoKey }
  } = state
  const { collection, video } = ownProps

  // The dialog needs a Video object passed in as a prop. Depending on the container that includes this dialog,
  // that video can be retrieved in a couple different ways.
  let selectedVideo, shouldUpdateCollection
  if (video) {
    selectedVideo = video
    shouldUpdateCollection = false
  } else if (collection) {
    selectedVideo = getVideoWithKey(collection, selectedVideoKey)
    shouldUpdateCollection = true
  }

  return {
    video:                  selectedVideo,
    shouldUpdateCollection: shouldUpdateCollection
  }
}

const ConnectedDeleteVideoDialog = connect(mapStateToProps)(DeleteVideoDialog)

export default ConnectedDeleteVideoDialog
