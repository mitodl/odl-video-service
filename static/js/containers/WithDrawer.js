// @flow
/* global SETTINGS: false */
import React from "react"
import * as R from "ramda"
import { connect } from "react-redux"

import * as commonUiActions from "../actions/commonUi"
import OVSToolbar from "../components/OVSToolbar"
import Drawer from "../components/material/Drawer"
import Footer from "../components/Footer"

class WithDrawer extends React.Component<*, void> {
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

const mapStateToProps = state => {
  const { collectionsList, commonUi } = state
  const collections = collectionsList.loaded ? collectionsList.data.results : []
  const needsUpdate = !collectionsList.processing && !collectionsList.loaded

  return {
    collections,
    commonUi,
    needsUpdate
  }
}

export default R.compose(connect(mapStateToProps))(WithDrawer)
