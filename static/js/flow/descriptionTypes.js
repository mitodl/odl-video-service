// @flow

/*
 * How a Collection or Video `description` is encoded.
 *
 * Mirrors `ui.constants.DescriptionFormat` on the server and the
 * DESCRIPTION_FORMAT_* constants in static/js/constants.js. A union rather than
 * `string` so that a typo in a comparison is a type error and not a branch that
 * silently never runs - getting this wrong renders markup as visible tags, or
 * escapes an author's formatting away.
 */
export type DescriptionFormat = "text" | "html"
