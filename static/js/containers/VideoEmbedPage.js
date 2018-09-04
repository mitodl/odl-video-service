// @flow
import React from "react"
import { connect } from "react-redux"
import type { Dispatch } from "redux"
import DocumentTitle from "react-document-title"

import { actions } from "../actions"
import VideoPlayer from "../components/VideoPlayer"
import type { Video, VideoUiState } from "../flow/videoTypes"
import { initGA, sendGAPageView } from "../util/google_analytics"
import { videoIsProcessing, videoHasError } from "../lib/video"

export class VideoEmbedPage extends React.Component<*, void> {
  props: {
    dispatch: Dispatch,
    video: Video,
    videoUi: VideoUiState
  }

  componentDidMount() {
    initGA()
    sendGAPageView(window.location.pathname)
  }

  updateCorner = (corner: string) => {
    const { dispatch } = this.props
    dispatch(actions.videoUi.updateVideoJsSync(corner))
  }

  renderBody() {
    const { video, videoUi } = this.props
    const videoStatus = this.getVideoStatus(video)
    if (videoStatus === "PROCESSING") {
      return this.renderProcessingMessage()
    } else if (videoStatus === "ERROR") {
      return this.renderErrorMessage()
    }
    return (
      <div className="embedded-video">
        <VideoPlayer
          video={video}
          cornerFunc={this.updateCorner}
          selectedCorner={videoUi.corner}
          embed={true}
        />
      </div>
    )
  }

  getVideoStatus(video: Video) {
    if (videoIsProcessing(video)) {
      return "PROCESSING"
    } else if (videoHasError(video)) {
      return "ERROR"
    }
    return "READY"
  }

  renderProcessingMessage() {
    return (
      <div className="processing-message">
        <h5>Video processing...</h5>
        <p>Please try again later.</p>
      </div>
    )
  }

  renderErrorMessage() {
    return (
      <div className="error-message">
        <h5>Error</h5>
        <p>Sorry, this video has an error.</p>
        <p>Please try again later.</p>
      </div>
    )
  }

  render() {
    const { video } = this.props
    return (
      <DocumentTitle title={`OVS | ${video.title} | Video Embed`}>
        {this.renderBody()}
      </DocumentTitle>
    )
  }
}

export const mapStateToProps = (state: { videoUi: VideoUiState }) => {
  const { videoUi } = state
  return {
    videoUi
  }
}

export const ConnectedVideoEmbedPage = connect(mapStateToProps)(VideoEmbedPage)

export default ConnectedVideoEmbedPage
