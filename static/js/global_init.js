// Define globals we would usually get from Django
import ReactDOM from "react-dom"
import { createRoot } from "react-dom/client"
import { makeVideo } from "./factories/video"

// For setting up enzyme with react adapter.
import { configure as configureEnzyme } from "enzyme"
import Adapter from "@wojtekmaj/enzyme-adapter-react-17"

// Configure enzyme with react adapter.
configureEnzyme({ adapter: new Adapter() })

const _createSettings = () => ({
  videoKey:              "a_video_key",
  video:                 makeVideo("a_video_key"),
  is_app_admin:          false,
  is_edx_course_admin:   false,
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

// workarounds for MDC and HTMLCanvasElement
global.cancelAnimationFrame = () => null
global.requestAnimationFrame = () => null
global.window.requestAnimationFrame = () => null
global.HTMLCanvasElement.prototype.getContext = () => {
  return {
    drawImage: function() {}
  }
}

// polyfill for Object.entries
import entries from "object.entries"
if (!Object.entries) {
  entries.shim()
}

// cleanup after each test run
// eslint-disable-next-line mocha/no-top-level-hooks
afterEach(function() {
  const node = document.querySelector("#integration_test_div")
  if (node) {
    // For React 18 compatibility
    if (node._reactRootContainer) {
      node._reactRootContainer.unmount()
    } else {
      // Fallback for older mounting patterns
      ReactDOM.unmountComponentAtNode(node)
    }
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
