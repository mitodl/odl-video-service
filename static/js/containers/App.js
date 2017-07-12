// @flow
import React from 'react';
import { connect } from 'react-redux';
import {} from '../actions';

class App extends React.Component {
  props: {
    dispatch: () => void,
  };

  render() {
    return null;
  }
}

const mapStateToProps = (state) => {  // eslint-disable-line no-unused-vars
  return {
  };
};

export default connect(mapStateToProps)(App);
