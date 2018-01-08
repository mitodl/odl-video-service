// @flow
import React from "react"
import { Route } from "react-router-dom"

import CollectionListPage from "../containers/CollectionListPage"
import CollectionDetailPage from "../containers/CollectionDetailPage"

import type { Match } from "react-router"

class CollectionsApp extends React.Component<*, void> {
  props: {
    match: Match
  }

  render() {
    const { match } = this.props
    return (
      <div className="app">
        <Route exact path={match.url} component={CollectionListPage} />
        <Route
          exact
          path={`${match.url}/:collectionKey`}
          component={CollectionDetailPage}
        />
      </div>
    )
  }
}

export default CollectionsApp
