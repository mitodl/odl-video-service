// @flow
import React from "react"

import Toolbar from "../components/material/Toolbar"

export default class OVSToolbar extends React.Component<*, void> {
  props: {
    setDrawerOpen: Function
  }

  render() {
    const { setDrawerOpen } = this.props

    return (
      <Toolbar onClickMenu={setDrawerOpen}>
        <a href="http://www.mit.edu">
          <img src="/static/images/mit_logo_grey_red.png" className="logo" />
        </a>
        <a className="title" href="/">
          ODL Video Services
        </a>
      </Toolbar>
    )
  }
}
