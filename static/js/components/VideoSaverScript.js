// @flow
/* global SETTINGS: false */
import React from "react"
import Script from "react-load-script"

const VideoSaverScript = () => {
  return (
    <Script
      url="https://www.dropbox.com/static/api/2/dropins.js"
      attributes={{
        id:             "dropboxjs",
        "data-app-key": SETTINGS.dropbox_key
      }}
    />
  )
}

export default VideoSaverScript
