import React from "react"

import VideoCard from "./VideoCard"

import type { Video } from "../types/videoTypes"

type Props = {
  className?: string
  style?: React.CSSProperties
  videos: Array<Video> | null
  isAdmin: boolean
  showDeleteVideoDialog: (videoKey: string) => void
  showEditVideoDialog: (videoKey: string) => void
  showShareVideoDialog: (videoKey: string) => void
  showVideoMenu: (videoKey: string) => void
  hideVideoMenu: (videoKey: string) => void
  isVideoMenuOpen: (videoKey: string) => boolean
  onReplaceVideo?: (videoKey: string, file: Record<string, unknown>) => void
}

export class VideoList extends React.Component<Props> {
  render() {
    const className = `video-list ${this.props.className || ""}`
    return (
      <div className={className} style={this.props.style}>
        {this.props.videos ?
          this.props.videos.map(video => this.renderVideoCard(video)) :
          null}
      </div>
    )
  }

  renderVideoCard(video: Video) {
    return (
      <VideoCard
        key={video.key}
        video={video}
        isAdmin={this.props.isAdmin}
        showDeleteVideoDialog={() =>
          this.props.showDeleteVideoDialog(video.key)
        }
        showEditVideoDialog={() => this.props.showEditVideoDialog(video.key)}
        showShareVideoDialog={() => this.props.showShareVideoDialog(video.key)}
        showVideoMenu={() => this.props.showVideoMenu(video.key)}
        hideVideoMenu={() => this.props.hideVideoMenu(video.key)}
        isMenuOpen={this.props.isVideoMenuOpen(video.key)}
        onReplaceVideo={
          this.props.onReplaceVideo ?
            file =>
              this.props.onReplaceVideo &&
                this.props.onReplaceVideo(video.key, file) :
            undefined
        }
      />
    )
  }
}

export default VideoList
