// Define globals we would usually get from Django
import ReactDOM from 'react-dom';
import { makeVideo } from './factories/video';

const _createSettings = () => ({
  videoKey: 'a_video_key',
  video: makeVideo('a_video_key'),
  editable: false,
  user: '',
  dropbox_key: 'dropbox_key',
  thumbnail_base_url: 'http://fake/',
  support_email_address: 'support@example.com'
});

global.SETTINGS = _createSettings();

// workarounds for MDC
global.cancelAnimationFrame = () => null;
global.requestAnimationFrame = () => null;

// polyfill for Object.entries
import entries from 'object.entries';
if (!Object.entries) {
  entries.shim();
}

// cleanup after each test run
afterEach(function () { // eslint-disable-line mocha/no-top-level-hooks
  let node = document.querySelector("#integration_test_div");
  if (node) {
    ReactDOM.unmountComponentAtNode(node);
  }
  document.body.innerHTML = '';
  global.SETTINGS = _createSettings();
  window.location = 'http://fake/';
});

// enable chai-as-promised
import chai from 'chai';
import chaiAsPromised from 'chai-as-promised';
chai.use(chaiAsPromised);
