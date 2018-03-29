// Define globals we would usually get from Django
import ReactDOM from "react-dom"
import sinon from "sinon"
import { makeVideo } from "./factories/video"

// For setting up enzyme with react adapter.
import { configure as configureEnzyme } from 'enzyme'
import Adapter from 'enzyme-adapter-react-15'

// Configure enzyme with react adapter.
configureEnzyme({ adapter: new Adapter() })

const _createSettings = () => ({
  videoKey:              "a_video_key",
  video:                 makeVideo("a_video_key"),
  editable:              false,
  user:                  "",
  dropbox_key:           "dropbox_key",
  thumbnail_base_url:    "http://fake/",
  support_email_address: "support@example.com",
  ga_dimension_camera:   "dimension1",
  FEATURES:              {
    ENABLE_VIDEO_PERMISSIONS: false
  }
})

global.SETTINGS = _createSettings()

// workarounds for MDC
global.cancelAnimationFrame = () => null
global.requestAnimationFrame = () => null

// polyfill for Object.entries
import entries from "object.entries"
if (!Object.entries) {
  entries.shim()
}

let sandbox
// eslint-disable-next-line mocha/no-top-level-hooks
before(() => {
  // eslint-disable-line mocha/no-top-level-hooks
  sandbox = sinon.sandbox.create()
  sandbox.stub(HTMLCanvasElement.prototype, "getContext").returns({
    drawImage: sandbox.stub()
  })
})

// eslint-disable-next-line mocha/no-top-level-hooks
after(() => {
  sandbox.restore()
})

// cleanup after each test run
// eslint-disable-next-line mocha/no-top-level-hooks
afterEach(function() {
  const node = document.querySelector("#integration_test_div")
  if (node) {
    ReactDOM.unmountComponentAtNode(node)
  }
  document.body.innerHTML = ""
  global.SETTINGS = _createSettings()
  window.location = "http://fake/"
})

// enable chai-as-promised
import chai from "chai"
import chaiAsPromised from "chai-as-promised"
chai.use(chaiAsPromised)
// create fake script tag to appease videojs-youtube
const script = document.createElement("script")
document.body.appendChild(script)
