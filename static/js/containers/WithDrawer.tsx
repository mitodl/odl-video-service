import React from "react"
import * as R from "ramda"
import { connect } from "react-redux"
import type { Dispatch } from "redux"

import * as commonUiActions from "../actions/commonUi"
import OVSToolbar from "../components/OVSToolbar"
import Drawer from "../components/material/Drawer"
import Footer from "../components/Footer"
import type { CollectionListItem } from "../types/collectionTypes"
import type { CommonUiState, RootState } from "../types/rootState"

type Props = {
  children?: React.ReactNode
  commonUi: CommonUiState
  dispatch: Dispatch
  /*
   * mapStateToProps below really does pass these two, and the connected
   * material/Drawer derives its own copies from the store rather than taking
   * them from here, so nothing in this component reads them. Declared because
   * they are part of the props this component is handed at runtime; dropping
   * them from mapStateToProps would be a behaviour change, not a conversion.
   */
  collections: Array<CollectionListItem>
  needsUpdate: boolean
}

class WithDrawer extends React.Component<Props> {
  setDrawerOpen = (open: boolean): void => {
    const { dispatch } = this.props
    dispatch(commonUiActions.setDrawerOpen(open))
  }

  render() {
    const { children, commonUi } = this.props

    return (
      <div>
        <OVSToolbar setDrawerOpen={this.setDrawerOpen.bind(this, true)} />
        <Drawer
          open={commonUi.drawerOpen}
          onDrawerClose={this.setDrawerOpen.bind(this, false)}
        />
        {children}
        <Footer />
      </div>
    )
  }
}

/*
 * `collectionsList.data` is the paginated response body the API returns --
 * `{ results: [...] }` -- not the bare array rootState.ts declares it to be.
 * Narrowed here rather than corrected there, since that file is out of scope
 * for this conversion; see the reported type gap.
 */
type CollectionsListResponse = {
  results: Array<CollectionListItem>
}

const mapStateToProps = (state: RootState) => {
  const { collectionsList, commonUi } = state
  const collections = collectionsList.loaded ?
    (collectionsList.data as unknown as CollectionsListResponse).results :
    []
  const needsUpdate = !collectionsList.processing && !collectionsList.loaded

  return {
    collections,
    commonUi,
    needsUpdate
  }
}

export default R.compose(connect(mapStateToProps))(WithDrawer)
