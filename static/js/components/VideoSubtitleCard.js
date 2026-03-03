// @flow
import React from "react"

import Card from "./material/Card"
import { makeVideoSubtitleUrl } from "../lib/urls"

import type { Video, VideoSubtitle } from "../flow/videoTypes"
import Filefield from "./material/Filefield"

export default class VideoSubtitleCard extends React.Component<*, void> {
  props: {
    video: Video,
    isAdmin: boolean,
    uploadVideoSubtitle: Function,
    deleteVideoSubtitle: Function
  }

  render() {
    const {
      video,
      isAdmin,
      uploadVideoSubtitle,
      deleteVideoSubtitle
    } = this.props
    return (
      <Card className="video-subtitle-card">
        <div className="video-subtitle-card-body">
          <h4 className="mdc-typography--subheading2">Subtitles / CC</h4>
          <div className="actions">
            <div className="video-subtitle-list">
              {video.videosubtitle_set.map(
                (subtitle: VideoSubtitle, key) => {
                  const filenameParts = subtitle.s3_object_key.split("/")
                  const fullFilename = filenameParts[filenameParts.length - 1]
                  const extension = fullFilename.split(".").pop()
                  return (
                    <div className="mdc-list-item" key={key}>
                      <span className="video-subtitle-filename">
                        {fullFilename.slice(0, 10)}..._{subtitle.language}.{extension}
                      </span>
                      <span className="video-subtitle-language">
                        ({subtitle.language_name})
                      </span>
                      <span className="video-subtitle-button">
                        <a
                          className="mdc-list-item mdc-link download-link"
                          href={makeVideoSubtitleUrl(subtitle)}
                          alt="Download this subtitle"
                        >
                          <i className="material-icons">file_download</i>
                        </a>
                      </span>
                      {isAdmin && (
                        <span className="video-subtitle-button">
                          <a
                            className="mdc-list-item mdc-link delete-btn"
                            onClick={() => deleteVideoSubtitle(subtitle.id)}
                          >
                            <i className="material-icons">delete</i>
                          </a>
                        </span>
                      )}
                    </div>
                  )
                }
              )}
            </div>
            <div className="video-subtitle-upload">
              {isAdmin && (
                <Filefield
                  id="video-subtitle"
                  accept=".vtt,.srt"
                  label="Add subtitles (.vtt or .srt file)"
                  onChange={uploadVideoSubtitle}
                />
              )}
            </div>
          </div>
        </div>
      </Card>
    )
  }
}
