// @flow
import React from 'react';

import Toolbar from '../components/material/Toolbar';

export default class OVSToolbar extends React.Component {
  props: {
    setDrawerOpen: Function
  };

  render() {
    const {setDrawerOpen} = this.props;

    return <Toolbar onClickMenu={setDrawerOpen}>
      <img src="/static/images/mit_logo_grey_red.png" className="logo"/>
      <a className="title" href="/">
        ODL Video Services
      </a>
    </Toolbar>;
  }
}
