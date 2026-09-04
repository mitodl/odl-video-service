// @flow
/* global SETTINGS: false */
import React from "react"
import { Route } from "react-router-dom"

import CollectionListPage from "./CollectionListPage"
import CollectionDetailPage from "./CollectionDetailPage"
import VideoDetailPage from "./VideoDetailPage"
import VideoEmbedPage from "./VideoEmbedPage"
import HelpPage from "./HelpPage"
import TermsPage from "./TermsPage"
import ToastOverlay from "./ToastOverlay"

import type { Match } from "react-router"

class App extends React.Component<*, void> {
  props: {
    match: Match
  }

  renderVideoEmbedPage = (routeProps: any) => {
    return <VideoEmbedPage video={SETTINGS.video} {...routeProps} />
  }

  renderVideoDetailPage = (routeProps: any) => {
    return (
      <VideoDetailPage
        videoKey={SETTINGS.videoKey}
        isAdmin={!!SETTINGS.is_video_admin}
        {...routeProps}
      />
    )
  }

  render() {
    const { match } = this.props
    return (
      <div className="app">
        <ToastOverlay />
        <Route
          exact
          path={`${match.url}collections/`}
          render={routeProps => <CollectionListPage {...routeProps} />}
        />
        <Route
          exact
          path={`${match.url}collections/:collectionKey/`}
          render={routeProps => <CollectionDetailPage {...routeProps} />}
        />
        <Route
          exact
          path={`${match.url}collections/:collectionKey/videos/:videoKey/`}
          component={this.renderVideoDetailPage}
        />
        <Route
          exact
          path={`${match.url}videos/:videoKey/`}
          component={this.renderVideoDetailPage}
        />
        <Route
          exact
          path={`${match.url}videos/:videoKey/embed/`}
          component={this.renderVideoEmbedPage}
        />
        <Route
          exact
          path={`${match.url}embeds/:videoKey/`}
          component={this.renderVideoEmbedPage}
        />
        <Route
          exact
          path={`${match.url}help/`}
          render={routeProps => <HelpPage {...routeProps} />}
        />
        <Route
          exact
          path={`${match.url}terms/`}
          render={routeProps => <TermsPage {...routeProps} />}
        />
      </div>
    )
  }
}

export default App
