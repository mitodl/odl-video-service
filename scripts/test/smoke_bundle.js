// Boots the built production bundle inside jsdom to prove the app still
// starts. The unit suite renders components in isolation and cannot catch a
// bundle that fails to initialise -- a module-init error, a broken createRoot,
// an unresolvable dependency -- which is the failure mode a React upgrade
// produces.
//
// No new dependencies: jsdom is already present, and webpack-stats.json already
// lists the entry chunks in load order -- the same list the Django template
// uses to emit <script> tags.
const fs = require("fs")
const path = require("path")
const vm = require("vm")
const { JSDOM } = require("jsdom")

const ROOT = path.resolve(__dirname, "../..")
const STATS = path.join(ROOT, "webpack-stats.json")

function readStats() {
  return JSON.parse(fs.readFileSync(STATS, "utf8"))
}

// webpack-stats lists each chunk's files in load order -- the same order the
// Django template emits <script> tags in. Follow it exactly.
function rootChunkFiles() {
  return readStats()
    .chunks.root.map(name => (typeof name === "string" ? name : name.name))
    .filter(name => name.endsWith(".js"))
    .map(name => path.join(ROOT, "static", "bundles", path.basename(name)))
    .filter(fs.existsSync)
}

// A dev build embeds webpack-hot-middleware, whose client opens a permanently
// pending EventSource to the dev server. Booting that in jsdom hangs rather
// than failing cleanly, so treat a dev build as "not built" and skip -- the
// alternative is a confusing timeout whenever someone has `docker-compose up`
// running locally.
function isDevBuild() {
  return readStats().chunks.root.some(name =>
    String(typeof name === "string" ? name : name.name).includes(
      "webpack-hot-middleware"
    )
  )
}

function bundleIsBuilt() {
  if (!fs.existsSync(STATS)) return false
  const stats = readStats()
  if (stats.status !== "done") return false
  if (!stats.chunks || !stats.chunks.root) return false
  if (isDevBuild()) return false
  return rootChunkFiles().length > 0
}

function bootBundle() {
  const errors = []

  const dom = new JSDOM(
    '<!doctype html><html><body><div id="container"></div></body></html>',
    { url: "http://fake/", runScripts: "outside-only", pretendToBeVisual: true }
  )
  const { window } = dom

  // The bundle reads these globals; they normally come from Django.
  window.SETTINGS = {
    public_path: "/static/bundles/",
    sentry_dsn: "",
    release_version: "test",
    environment: "test",
    videoKey: "a_video_key",
    user: "",
    email: "",
    is_app_admin: false,
    is_edx_course_admin: false,
    dropbox_key: "dropbox_key",
    thumbnail_base_url: "http://fake/",
    support_email_address: "support@example.com",
    ga_dimension_camera: "dimension1",
    FEATURES: { ENABLE_VIDEO_PERMISSIONS: false }
  }
  window.requestAnimationFrame = cb => window.setTimeout(cb, 0)
  window.cancelAnimationFrame = id => window.clearTimeout(id)
  window.HTMLCanvasElement.prototype.getContext = () => ({ drawImage() {} })
  window.console.error = (...args) => errors.push(args.join(" "))

  for (const file of rootChunkFiles()) {
    const name = path.basename(file)

    // Webpack's automatic publicPath runtime resolves its own URL from
    // document.currentScript.src, falling back to the last <script> tag in the
    // document. vm.runInContext provides neither, so the bundle throws
    // "Automatic publicPath is not supported in this browser" before any app
    // code runs. Appending a matching <script src> makes the fallback resolve,
    // which is what a real browser would present.
    const tag = window.document.createElement("script")
    tag.src = `http://fake/static/bundles/${name}`
    window.document.head.appendChild(tag)

    try {
      vm.runInContext(
        fs.readFileSync(file, "utf8"),
        dom.getInternalVMContext(),
        { filename: file }
      )
    } catch (e) {
      errors.push(`${name}: ${e.message}`)
    }
  }

  return { container: window.document.getElementById("container"), errors }
}

module.exports = { bootBundle, bundleIsBuilt, rootChunkFiles, isDevBuild }
