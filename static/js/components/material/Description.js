// @flow
import React from "react"

import { DESCRIPTION_FORMAT_HTML } from "../../constants"

type DescriptionProps = {
  description: ?string,
  descriptionFormat: ?string,
  className?: string
}

/**
 * Render a Collection or Video description in whichever format it is stored in.
 *
 * The two cannot share a render path. Rich text is markup and has to be
 * injected; plain text must not be, or a description containing `a <b to c` is
 * read as an unterminated tag and everything after it disappears from the page.
 *
 * Which one a description is comes from `description_format` on the record, not
 * from inspecting the value - see ui/constants.py. That matters most for the
 * descriptions that were already in the database when rich text arrived: they
 * are plain text, they are rendered escaped exactly as they always were, and
 * they only start being treated as markup once an author upgrades them.
 */
export default class Description extends React.Component<*, void> {
  props: DescriptionProps

  render() {
    const { description, descriptionFormat, className } = this.props

    if (!description) {
      return null
    }

    if (descriptionFormat === DESCRIPTION_FORMAT_HTML) {
      // Safe to inject: every write path sanitizes against the allowlist in
      // ui/html.py before the value is stored.
      return (
        <div
          className={className}
          dangerouslySetInnerHTML={{ __html: description }}
        />
      )
    }

    /*
     * Rendered as text, so React escapes it. `description-plain-text` supplies
     * `white-space: pre-wrap`, which is what keeps the author's line breaks
     * visible - in plain text those carried the only structure there was, and
     * HTML would otherwise collapse them into single spaces.
     */
    return (
      <div className={`${className || ""} description-plain-text`.trim()}>
        {description}
      </div>
    )
  }
}
