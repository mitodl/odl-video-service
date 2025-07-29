// @flow
/* global SETTINGS: false */
import React from "react"
import { Routes, Route, useParams, useLocation } from "react-router-dom"
import ga from "react-ga"

import CollectionListPage from "./CollectionListPage"
import CollectionDetailPage from "./CollectionDetailPage"
import VideoDetailPage from "./VideoDetailPage"
import VideoEmbedPage from "./VideoEmbedPage"
import HelpPage from "./HelpPage"
import TermsPage from "./TermsPage"
import ToastOverlay from "./ToastOverlay"

// Google Analytics tracking hook
function usePageTracking() {
  const location = useLocation()

  React.useEffect(() => {
    if (SETTINGS.gaTrackingID) {
      ga.pageview(location.pathname)
    }
  }, [location])
}

// Wrapper components to handle route parameters
function VideoDetailPageWrapper() {
  const { videoKey, collectionKey } = useParams()
  return (
    <VideoDetailPage
      videoKey={videoKey || SETTINGS.videoKey}
      isAdmin={!!SETTINGS.is_video_admin}
    />
  )
}

function VideoEmbedPageWrapper() {
  const { videoKey } = useParams()
  return <VideoEmbedPage video={SETTINGS.video} videoKey={videoKey} />
}

function CollectionDetailPageWrapper() {
  const { collectionKey } = useParams()
  return <CollectionDetailPage collectionKey={collectionKey} />
}

function App() {
  usePageTracking()

  return (
    <div className="app">
      <ToastOverlay />
      <Routes>
        <Route
          path="collections"
          element={<CollectionListPage />}
        />
        <Route
          path="collections/:collectionKey"
          element={<CollectionDetailPageWrapper />}
        />
        <Route
          path="collections/:collectionKey/videos/:videoKey"
          element={<VideoDetailPageWrapper />}
        />
        <Route
          path="videos/:videoKey"
          element={<VideoDetailPageWrapper />}
        />
        <Route
          path="videos/:videoKey/embed"
          element={<VideoEmbedPageWrapper />}
        />
        <Route
          path="embeds/:videoKey"
          element={<VideoEmbedPageWrapper />}
        />
        <Route path="help" element={<HelpPage />} />
        <Route path="terms" element={<TermsPage />} />
      </Routes>
    </div>
  )
}

export default App
