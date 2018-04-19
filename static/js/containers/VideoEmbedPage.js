// @flow
import React from "react"
import { connect } from "react-redux"
import type { Dispatch } from "redux"
import DocumentTitle from "react-document-title"

import { actions } from "../actions"
import VideoPlayer from "../components/VideoPlayer"
import type { Video, VideoUiState } from "../flow/videoTypes"
import { initGA, sendGAPageView } from "../util/google_analytics"

class VideoEmbedPage extends React.Component<*, void> {
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

  render() {
    const { video, videoUi } = this.props

    return (
      <DocumentTitle title={`OVS | ${video.title} | Video Embed`}>
        <div className="embedded-video">
          <VideoPlayer
            video={video}
            cornerFunc={this.updateCorner}
            selectedCorner={videoUi.corner}
            embed={true}
          />
        </div>
      </DocumentTitle>
    )
  }
}

const mapStateToProps = state => {
  const { videoUi } = state
  return {
    videoUi
  }
}

export default connect(mapStateToProps)(VideoEmbedPage)
