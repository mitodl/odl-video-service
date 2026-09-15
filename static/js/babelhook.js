const { babelSharedLoader } = require("../../webpack.config.shared")
const whatwgURL = require("whatwg-url")
const { v4: uuidv4 } = require("uuid")
require("babel-polyfill")

// Update presets to use Babel 7 format for testing
babelSharedLoader.options.presets = ["@babel/preset-env", "@babel/preset-react"]

// webpack.config.shared.js declares ignore as the relative glob
// "node_modules/**", which @babel/register anchors to cwd. That covers this
// checkout's own node_modules but nothing resolved from a node_modules
// directory further up the tree -- which happens whenever this repo sits
// inside another copy of itself, as a nested git worktree does. Such a module
// would then be transformed, react-hot-loader/babel would inject its
// enterModule/leaveModule calls into it, and the resulting circular requires
// print Node "Accessing non-existent property" warnings that fail the run.
// A regexp has no anchor, so it ignores every node_modules regardless of
// where it was resolved from. Test-runner only; the webpack build keeps the
// glob, and its babel-loader rule already carries exclude: /node_modules/.
babelSharedLoader.options.ignore = [/node_modules/]

// jsdom initialization here adapted from https://airbnb.io/enzyme/docs/guides/jsdom.html
const { JSDOM } = require("jsdom")
const jsdom = new JSDOM("<!doctype html><html><body></body></html>", {
  url: "http://fake/"
})
const { window } = jsdom

const { polyfill } = require("raf")
polyfill(global)
polyfill(window)

// sketchy polyfill :/
URL.createObjectURL = function() {
  const url = new URL("http://fake/")
  url.path = []
  const objectURL = `blob:${whatwgURL.serializeURL(url)}/${uuidv4()}`
  return objectURL
}

function copyProps(src, target) {
  Object.defineProperties(target, {
    ...Object.getOwnPropertyDescriptors(src),
    ...Object.getOwnPropertyDescriptors(target)
  })
}

// Patch dispatchEvent to handle custom events properly in jsdom v26
// This must happen before other scripts load to override jsdom's strict validation
const originalDispatchEvent = window.EventTarget.prototype.dispatchEvent
window.EventTarget.prototype.dispatchEvent = function(event) {
  try {
    // Try the original first
    return originalDispatchEvent.call(this, event)
  } catch (error) {
    // If it fails due to invalid event type, create a proper event
    if (
      error.message.includes("not of type 'Event'") ||
      error.message.includes("parameter 1 is not of type 'Event'")
    ) {
      let eventName = "custom"
      let eventData = {}

      if (typeof event === "string") {
        eventName = event
      } else if (event && typeof event === "object") {
        eventName = event.type || event.name || "custom"
        eventData = event
      }

      const customEvent = new window.CustomEvent(eventName, {
        detail:     eventData,
        bubbles:    true,
        cancelable: true
      })

      return originalDispatchEvent.call(this, customEvent)
    }
    // Re-throw other errors
    throw error
  }
}

// Proxy window.location assignments to use jsdom.reconfigure()
// instead of direct assignment, which is no longer allowed in v26
const windowProxy = new Proxy(window, {
  set: function(target, prop, value) {
    if (prop === "location") {
      let url = value
      if (!url.startsWith("http")) {
        url = `http://fake${url}`
      }
      jsdom.reconfigure({ url })
      return true
    }

    return Reflect.set(target, prop, value)
  }
})

global.window = windowProxy
global.document = windowProxy.document
global.navigator = {
  userAgent: "node.js"
}
global.requestAnimationFrame = function(callback) {
  return setTimeout(callback, 0)
}
global.cancelAnimationFrame = function(id) {
  clearTimeout(id)
}
copyProps(window, global)

require("@babel/register")(babelSharedLoader.options)
