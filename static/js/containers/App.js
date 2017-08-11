// @flow
import React from 'react';
import type { Match } from 'react-router';

export default class App extends React.Component {
  props: {
    match: Match
  };

  render() {
    return (
      <div
        // routes go in children here
        className="app">
      </div>
    );
  }
}
