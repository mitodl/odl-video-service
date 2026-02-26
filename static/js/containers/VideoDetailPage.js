// @flow
/* global SETTINGS: false */
import React from "react"
import { connect } from "react-redux"
import moment from "moment"
import type { Dispatch } from "redux"
import * as R from "ramda"
import _ from "lodash"
import DocumentTitle from "react-document-title"

import Button from "../components/material/Button"
import Drawer from "../components/material/Drawer"
import OVSToolbar from "../components/OVSToolbar"
import Footer from "../components/Footer"
import VideoPlayer from "../components/VideoPlayer"
import EditVideoFormDialog from "../components/dialogs/EditVideoFormDialog"
import ShareVideoDialog from "../components/dialogs/ShareVideoDialog"
import DeleteVideoDialog from "../components/dialogs/DeleteVideoDialog"
import DeleteSubtitlesDialog from "../components/dialogs/DeleteSubtitlesDialog"
import { withDialogs } from "../components/dialogs/hoc"
import VideoSubtitleCard from "../components/VideoSubtitleCard"
import VideoSaverScript from "../components/VideoSaverScript"
import { ConnectedVideoAnalyticsOverlay } from "./VideoAnalyticsOverlay"
import ToastOverlay from "./ToastOverlay"

import { actions } from "../actions"
import { setDrawerOpen } from "../actions/commonUi"
import { makeCollectionUrl } from "../lib/urls"
import { saveToDropbox } from "../lib/video"
import { videoIsProcessing, videoHasError } from "../lib/video"
import { DIALOGS, MM_DD_YYYY } from "../constants"
import { initGA, sendGAPageView } from "../util/google_analytics"

import type { Video, VideoUiState } from "../flow/videoTypes"
import type { Collection } from "../flow/collectionTypes"
import type { CommonUiState } from "../reducers/commonUi"

export class VideoDetailPage extends React.Component<*, void> {
  props: {
    dispatch: Dispatch,
    video: ?Video,
    collection: ?Collection,
    videoKey: string,
    needsUpdate: boolean,
    collectionNeedsUpdate: boolean,
    commonUi: CommonUiState,
    videoUi: VideoUiState,
    showDialog: Function,
    isAdmin: boolean,
    dialogProps: Object
  }

  videoPlayerRef: Object

  componentDidMount() {
    this.setCurrentVideoKey()
    this.updateRequirements()
    initGA()
    sendGAPageView(window.location.pathname)
  }

  componentDidUpdate() {
    this.updateRequirements()
  }

  setCurrentVideoKey = () => {
    const { dispatch, videoKey } = this.props
    dispatch(actions.videoUi.setCurrentVideoKey({ videoKey }))
  }

  updateRequirements = () => {
    const { dispatch, videoKey, needsUpdate, video, collection, collectionNeedsUpdate } = this.props

    if (needsUpdate) {
      dispatch(actions.videos.get(videoKey))
    }

    // Fetch collection if video exists and collection needs update
    if (collectionNeedsUpdate && video && video.collection_key) {
      dispatch(actions.collections.get(video.collection_key))
    }
  }

  setDrawerOpen = (open: boolean): void => {
    const { dispatch } = this.props
    dispatch(setDrawerOpen(open))
  }

  uploadVideoSubtitle = async () => {
    const {
      dispatch,
      video,
      videoKey,
      videoUi: { videoSubtitleForm }
    } = this.props
    if (video && videoSubtitleForm.subtitle) {
      const formData = new FormData()
      formData.append("file", videoSubtitleForm.subtitle)
      formData.append("collection", video.collection_key)
      formData.append("video", video.key)
      formData.append("language", videoSubtitleForm.language)
      // $FlowFixMe: A file always has a name
      formData.append("filename", videoSubtitleForm.subtitle.name)
      await dispatch(actions.videoSubtitles.post(formData))
      dispatch(actions.videos.get(videoKey))
    }
  }

  setUploadSubtitle = async (event: Object) => {
    const { dispatch } = this.props
    await dispatch(actions.videoUi.setUploadSubtitle(event.target.files[0]))
    this.uploadVideoSubtitle()
    dispatch(
      actions.toast.addMessage({
        message: {
          key:     "subtitles-uploaded",
          content: "Subtitles uploaded",
          icon:    "check"
        }
      })
    )
  }

  updateCorner = (corner: string) => {
    const { dispatch } = this.props
    dispatch(actions.videoUi.updateVideoJsSync(corner))
  }

  showDeleteSubtitlesDialog = (subtitlesKey: string | number) => {
    const { dispatch, showDialog } = this.props
    dispatch(actions.videoUi.setCurrentSubtitlesKey({ subtitlesKey }))
    showDialog(DIALOGS.DELETE_SUBTITLES)
  }

  render() {
    const { video, commonUi, isAdmin, showDialog } = this.props
    if (!video) {
      return null
    }

    const formattedCreation = moment(video.created_at).format(MM_DD_YYYY)
    const collectionUrl = makeCollectionUrl(video.collection_key)
    return (
      <DocumentTitle title={`OVS | ${video.title} | Video Detail`}>
        <div>
          <ToastOverlay />
          <VideoSaverScript />
          <OVSToolbar setDrawerOpen={this.setDrawerOpen.bind(this, true)} />
          <Drawer
            open={commonUi.drawerOpen}
            onDrawerClose={this.setDrawerOpen.bind(this, false)}
          />

          {video ? this.renderVideoPlayer(video) : null}

          <div className="mdc-layout-grid mdc-video-detail">
            <div className="mdc-layout-grid__inner">
              <div className="summary mdc-layout-grid__cell--span-7">
                <div className="card video-summary-card">
                  <p className="channelLink mdc-typography--subheading1">
                    <a className="collection-link" href={collectionUrl}>
                      {video.collection_title}
                    </a>
                  </p>
                  <h1 className="video-title mdc-typography--title">
                    {video.title}
                  </h1>
                  <div className="actions">
                    <Button
                      className="share mdc-button--raised"
                      onClick={showDialog.bind(this, DIALOGS.SHARE_VIDEO)}
                    >
                      Share
                    </Button>
                    {isAdmin && (
                      <span>
                        <Button
                          className="edit mdc-button--raised"
                          onClick={showDialog.bind(this, DIALOGS.EDIT_VIDEO)}
                        >
                          Edit
                        </Button>
                        <Button
                          className="dropbox mdc-button--raised"
                          onClick={saveToDropbox.bind(this, video)}
                        >
                          Save To Dropbox
                        </Button>
                        <Button
                          className="delete mdc-button--raised"
                          onClick={showDialog.bind(this, DIALOGS.DELETE_VIDEO)}
                        >
                          Delete
                        </Button>
                        <Button
                          className="analytics mdc-button--raised"
                          onClick={() => this.toggleAnalyticsOverlay()}
                        >
                          Show/Hide Analytics
                        </Button>
                      </span>
                    )}
                  </div>
                  {video.description && (
                    <p className="video-description mdc-typography--body1">
                      {video.description}
                    </p>
                  )}
                  <div className="upload-date mdc-typography--subheading1 fontgray">
                    Uploaded {formattedCreation}
                  </div>
                </div>
              </div>
              <div className="video-subtitles mdc-layout-grid__cell--span-5">
                <VideoSubtitleCard
                  id="subtitleCard"
                  video={video}
                  isAdmin={isAdmin}
                  uploadVideoSubtitle={this.setUploadSubtitle}
                  deleteVideoSubtitle={this.showDeleteSubtitlesDialog}
                />
              </div>
            </div>
          </div>
          <Footer />
        </div>
      </DocumentTitle>
    )
  }

  toggleAnalyticsOverlay = () => {
    this.props.dispatch(actions.videoUi.toggleAnalyticsOverlay())
  }

  renderVideoPlayer = (video: Video) => {
    const { videoUi } = this.props
    if (videoIsProcessing(video)) {
      return (
        <div className="video-message">
          Video is processing, check back later
        </div>
      )
    }

    if (videoHasError(video)) {
      return <div className="video-message">Something went wrong :(</div>
    }

    return (
      <div
        className="video-player-container"
        style={{
          position: "relative"
        }}
      >
        <VideoPlayer
          id="video-player"
          videoPlayerRef={ref => {
            this.videoPlayerRef = ref
          }}
          video={video}
          cornerFunc={this.updateCorner}
          selectedCorner={videoUi.corner}
          overlayChildren={this.renderOverlayChildren()}
        />
      </div>
    )
  }

  renderOverlayChildren() {
    return [this.renderAnalyticsOverlay()]
  }

  renderAnalyticsOverlay() {
    const { video } = this.props
    const {
      analyticsOverlayIsVisible,
      videoTime,
      duration
    } = this.props.videoUi
    if (!analyticsOverlayIsVisible) {
      return null
    }
    const overlayPadding = "10px"
    return (
      <div
        key="analytics-overlay"
        className="analytics-overlay-container"
        style={{
          position:        "absolute",
          bottom:          "2.5em",
          left:            "8%",
          right:           "8%",
          height:          "45%",
          minHeight:       "250px",
          opacity:         ".9",
          backgroundColor: "hsla(0, 0%, 90%, 1)",
          borderRadius:    "5px"
        }}
      >
        <div
          style={{
            position: "absolute",
            top:      overlayPadding,
            left:     overlayPadding,
            right:    overlayPadding,
            bottom:   overlayPadding
          }}
        >
          <ConnectedVideoAnalyticsOverlay
            id="video-analytics-overlay"
            video={video}
            currentTime={videoTime || 0}
            duration={duration || 0}
            setVideoTime={(...args) => {
              this.setVideoTime(...args)
            }}
            style={{ width: "100%", height: "100%" }}
            showCloseButton={true}
            onClose={this.toggleAnalyticsOverlay}
          />
        </div>
      </div>
    )
  }

  setVideoTime(time: number) {
    if (this.videoPlayerRef) {
      this.videoPlayerRef.setCurrentTime(time)
    }
  }
}

const mapStateToProps = (state, ownProps) => {
  const { videoKey } = ownProps
  const { videos, collections, commonUi, videoUi } = state
  const video =
    videos.data && _.isFunction(videos.data.get) ?
      videos.data.get(videoKey) :
      null
  const needsUpdate = !videos.processing && !videos.loaded

  // Get the collection if video exists
  const collection = video && collections.data && collections.data.key === video.collection_key ?
    collections.data :
    null

  // Only fetch collection if not processing and either not loaded or wrong collection
  const collectionNeedsUpdate = video && video.collection_key &&
    !collections.processing &&
    (!collection || (collections.data && collections.data.key !== video.collection_key))

  const dialogProps = {
    [DIALOGS.EDIT_VIDEO]: {
      video,
      collection
    }
  }

  return {
    video,
    collection,
    collectionNeedsUpdate,
    needsUpdate,
    commonUi,
    videoUi,
    dialogProps
  }
}

export default R.compose(
  connect(mapStateToProps),
  withDialogs([
    { name: DIALOGS.EDIT_VIDEO, component: EditVideoFormDialog },
    { name: DIALOGS.SHARE_VIDEO, component: ShareVideoDialog },
    { name: DIALOGS.DELETE_VIDEO, component: DeleteVideoDialog },
    { name: DIALOGS.DELETE_SUBTITLES, component: DeleteSubtitlesDialog }
  ])
)(VideoDetailPage)
