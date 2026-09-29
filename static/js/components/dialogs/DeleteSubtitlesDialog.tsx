import React from "react"
import _ from "lodash"
import { connect } from "react-redux"
import type { UnknownAction } from "redux"
import type { ThunkAction, ThunkDispatch } from "redux-thunk"

import Dialog from "../material/Dialog"

import { actions } from "../../actions"

import type { RootState } from "../../types/rootState"
import type { ActionCreator } from "../../types/reduxTypes"
import type { VideoSubtitle } from "../../types/videoTypes"

/*
 * redux-hammock derives the REST slices at runtime, so actions/index.ts can
 * only type them as `RestActions` -- an index signature of
 * `(...args: any[]) => any`. These three local types narrow the slices this
 * dialog touches back to real signatures. Each cast is erased at runtime --
 * the calls stay property accesses on `actions.videoSubtitles`,
 * `actions.toast` and `actions.videos`, which is what the tests stub.
 */
type VideoSubtitlesActions = {
  delete: (
    id: number
  ) => ThunkAction<Promise<unknown>, RootState, unknown, UnknownAction>
}

type ToastActions = {
  addMessage: ActionCreator
}

type VideosActions = {
  get: (
    videoKey: string
  ) => ThunkAction<Promise<unknown>, RootState, unknown, UnknownAction>
}

type Props = {
  dispatch: ThunkDispatch<RootState, unknown, UnknownAction>
  open: boolean
  hideDialog: () => void
  // The connected container maps this from the store, where it is absent until
  // a subtitles file is selected; `render` returns null in that case.
  subtitlesFile: VideoSubtitle | null | undefined
  videoKey: string
}

export class DeleteSubtitlesDialog extends React.Component<Props> {
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
    await dispatch(
      (actions.videoSubtitles as VideoSubtitlesActions).delete(
        (subtitlesFile as VideoSubtitle).id
      )
    )
  }

  addToastMessage = () => {
    this.props.dispatch(
      (actions.toast as ToastActions).addMessage({
        message: {
          key:     "subtitles-deleted",
          content: "Subtitles file deleted",
          icon:    "check"
        }
      })
    )
  }

  updateVideo = () => {
    this.props.dispatch(
      (actions.videos as VideosActions).get(this.props.videoKey)
    )
  }
}

export const mapStateToProps = (state: RootState) => {
  const { videoUi, videos } = state
  /*
   * `currentVideoKey` is `string | null` and `currentSubtitlesKey` is
   * `string | number | null` in the store, but this dialog is only mounted for
   * the video and subtitles file currently being viewed, so the lookups and
   * the `videoKey` prop are narrowed here. Every cast is erased at runtime.
   */
  const { currentVideoKey, currentSubtitlesKey } = videoUi
  const video = videos.data.get(currentVideoKey as string)
  let subtitlesFile: VideoSubtitle | null | undefined = null
  if (video) {
    subtitlesFile = _.find(video.videosubtitle_set, {
      id: currentSubtitlesKey as number
    })
  }
  return { subtitlesFile, videoKey: currentVideoKey as string }
}

const ConnectedDeleteSubtitlesDialog = connect(mapStateToProps)(
  DeleteSubtitlesDialog
)

export default ConnectedDeleteSubtitlesDialog
