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
    // Sent by ui/views.py:68 and read by util/google_analytics and
    // util/withTracker, but absent from the old Flow declaration.
    gaTrackingID: string
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
    // Sent by ui/views.py:83 and read by EditVideoFormDialog to cap the
    // thumbnail upload; absent from the old Flow declaration.
    thumbnail_upload_max_size: number
    status_code?: number
    ga_dimension_camera: string
    sentry_dsn: string
    release_version: string
    environment: string
  }

  const videojs: (...args: any[]) => any

  // Dev/test hooks that static/js/lib/api.ts reads off window to stub the
  // analytics endpoint. Set by the browser console or a test, never by the app.
  interface Window {
    // Injected by the Redux DevTools browser extension; absent in production
    // and in tests, which is why store/configureStore falls back to `compose`.
    __REDUX_DEVTOOLS_EXTENSION_COMPOSE__?: typeof import("redux").compose
    ovsMockAnalytics?: boolean
    ovsMockAnalyticsData?: unknown
    ovsMockAnalyticsError?: boolean
  }
}

export {}
