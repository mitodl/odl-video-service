// @flow
import React from 'react';
import { shallow } from 'enzyme';
import { assert } from 'chai';
import USwitchPlayer from './USwitchPlayer';

describe("USwitchPlayer", () => {
  let renderVideoPlayer = () => {
    return shallow(
      <USwitchPlayer  />, {
        context: {
          router: {}
        }
      }
    );
  };

  it('div element with id of omniPlayer is rendered', () => {
    let wrapper = renderVideoPlayer();
    assert.equal(wrapper.html(),'<div allowfullscreen="" id="omniPlayer"><video id="video"></video></div>');
  });
});
