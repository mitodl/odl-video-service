import React from "react"
import { Route } from "react-router-dom"

import CollectionListPage from "./CollectionListPage"
import CollectionDetailPage from "./CollectionDetailPage"
import VideoDetailPage from "./VideoDetailPage"
import VideoEmbedPage from "./VideoEmbedPage"
import HelpPage from "./HelpPage"
import TermsPage from "./TermsPage"
import ToastOverlay from "./ToastOverlay"

/*
 * react-router 4 ships no type declarations and @types/react-router is not
 * installed, so the one member of `match` this component reads is declared
 * here rather than pulling in a types package for a single field.
 */
type Match = {
  url: string
}

type Props = {
  match: Match
  // react-router's Route passes location alongside match, and withTracker --
  // which wraps this component in Router.tsx -- reads location.pathname to
  // report the page view. It was never declared.
  location: {
    pathname: string
  }
}

class App extends React.Component<Props> {
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
