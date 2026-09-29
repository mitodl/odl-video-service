// webpack rewrites this bare assignment into `__webpack_require__.p = ...`,
// so it has to stay exactly this shape to keep working at runtime.
// @types/webpack-env declares the binding as a mutable var, so it typechecks.
__webpack_public_path__ = SETTINGS.public_path // eslint-disable-line no-undef, camelcase
import "../../scss/layout.scss"
