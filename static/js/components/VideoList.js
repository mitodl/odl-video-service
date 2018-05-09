// @flow
import React from "react"

import VideoCard from "./VideoCard"


export class VideoList extends React.Component<*, void> {
  props: {
    className?: string,
    style?: {[string]: any},
    videos: ?Array<Video>,
    isAdmin: boolean,
    showDeleteVideoDialog: Function,
    showEditVideoDialog: Function,
    showShareVideoDialog: Function,
    showVideoMenu: Function,
    hideVideoMenu: Function,
    isVideoMenuOpen: Function,
  }

  render () {
    const className = `video-list ${this.props.className || ''}`
    return (
      <div className={className} style={this.props.style}>
        {
          this.props.videos ?
            this.props.videos.map((video) => this.renderVideoCard(video))
            : null
        }
      </div>
    )
  }

  renderVideoCard (video:Video) {
    return (
      <VideoCard
        key={video.key}
        video={video}
        isAdmin={this.props.isAdmin}
        showDeleteVideoDialog={() => this.props.showDeleteVideoDialog(video.key)}
        showEditVideoDialog={() => this.props.showEditVideoDialog(video.key)}
        showShareVideoDialog={() => this.props.showShareVideoDialog(video.key)}
        showVideoMenu={() => this.props.showVideoMenu(video.key)}
        hideVideoMenu={() => this.props.hideVideoMenu(video.key)}
        isMenuOpen={this.props.isVideoMenuOpen(video.key)}
      />
    )
  }
}

export default VideoList
