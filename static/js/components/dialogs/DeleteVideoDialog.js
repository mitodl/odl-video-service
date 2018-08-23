// @flow
import React from "react"
import { connect } from "react-redux"
import type { Dispatch } from "redux"

import Dialog from "../material/Dialog"

import { actions } from "../../actions"
import { getVideoWithKey } from "../../lib/collection"
import { makeCollectionUrl } from "../../lib/urls"

import type { Video } from "../../flow/videoTypes"

type DialogProps = {
  dispatch: Dispatch,
  open: boolean,
  hideDialog: Function,
  shouldUpdateCollection: boolean,
  video: Video,
  window?: any
}

export class DeleteVideoDialog extends React.Component<*, void> {
  props: DialogProps

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

export const mapStateToProps = (state: Object, ownProps: Object) => {
  const { collectionUi: { selectedVideoKey } } = state
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
