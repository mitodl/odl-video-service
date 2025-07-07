const { babelSharedLoader } = require("../../webpack.config.shared")
const idlUtils = require("jsdom/lib/jsdom/living/generated/utils")
const whatwgURL = require("whatwg-url")
const { v4: uuidv4 } = require('uuid')
require("babel-polyfill")

// Update presets to use Babel 7 format for testing
babelSharedLoader.options.presets = ["@babel/preset-env", "@babel/preset-react"]

// window and global must be defined here before React is imported
require("jsdom-global")(undefined, {
  url: "http://fake/"
})

const changeURL = (window, urlString) => {
  const doc = idlUtils.implForWrapper(window._document)
  doc._URL = whatwgURL.parseURL(urlString)
  doc._origin = whatwgURL.serializeURLOrigin(doc._URL)
}

// sketchy polyfill :/
URL.createObjectURL = function() {
  const url = new URL("http://fake/")
  url.path = []
  const objectURL = `blob:${whatwgURL.serializeURL(url)}/${uuidv4()}`
  return objectURL
}

// We need to explicitly change the URL when window.location is used
Object.defineProperty(window, "location", {
  set: value => {
    if (!value.startsWith("http")) {
      value = `http://fake${value}`
    }
    changeURL(window, value)
  }
})

require("@babel/register")(babelSharedLoader.options)
