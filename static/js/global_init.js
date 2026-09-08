// Define globals we would usually get from Django
import { cleanup } from "@testing-library/react"
import { makeVideo } from "./factories/video"
import suppressVendorLifecycleWarnings from "./testUtils/suppressVendorLifecycleWarnings"

// Installed once for the whole process, not per test file: React dedupes each
// deprecated-lifecycle warning once per component class, so only the first
// file to mount a given vendored component can see it. See the helper for the
// list of dependencies this covers and what removes each one.
suppressVendorLifecycleWarnings()

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
// Exported so teardown_test.js can exercise this exact function without
// depending on mocha's hook ordering between two separate `it` blocks.
export function resetTestEnvironment() {
  // Unmount React trees before detaching the DOM. RTL's auto-cleanup would
  // still unmount without this -- it holds a direct reference to its own
  // container, so the innerHTML reset below does not prevent it -- but that
  // ordering means componentWillUnmount runs against an already-detached
  // node. Dialog/Drawer/Menu call MDC .destroy() there and VideoPlayer
  // disposes its video.js player, so they should see an attached DOM.
  // Calling cleanup() explicitly also removes any dependence on mocha's
  // hook registration order. It is a no-op when RTL rendered nothing.
  cleanup()
  document.body.innerHTML = ""
  global.SETTINGS = _createSettings()
  window.location = "http://fake/"
}

// eslint-disable-next-line mocha/no-top-level-hooks
afterEach(resetTestEnvironment)

// enable chai-as-promised
import chai from "chai"
import chaiAsPromised from "chai-as-promised"
chai.use(chaiAsPromised)
// create fake script tag to appease videojs-youtube
const script = document.createElement("script")
document.body.appendChild(script)
