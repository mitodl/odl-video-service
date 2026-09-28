import type { Video } from "./videoTypes"

// Ambient globals the app reads off `window` or that the bundler injects.
// This file has a top-level import, so it is a module; the declarations have
// to be wrapped in `declare global` to stay ambient.
declare global {
  const SETTINGS: {
    public_path: string
    FEATURES: {
      [key: string]: boolean
    }
    reactGaDebug: string
    cloudfront_base_url: string
    video: Video
    videoKey: string
    is_video_admin?: boolean
    is_app_admin: boolean
    is_edx_course_admin: boolean
    user: string | null
    email: string | null
    dropbox_key: string
    support_email_address: string
    status_code?: number
    ga_dimension_camera: string
    sentry_dsn: string
    release_version: string
    environment: string
  }

  // webpack
  // eslint-disable-next-line camelcase
  const __webpack_public_path__: string

  const videojs: (...args: any[]) => any
}

export {}
