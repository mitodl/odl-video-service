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
      <span className="title">
        ODL Video Services
      </span>
    </Toolbar>;
  }
}
