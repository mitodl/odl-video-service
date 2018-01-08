// @flow
/* global SETTINGS:false */
import React from "react"

import { adminFAQs, viewerFAQs } from "../data/faqs"

export default class FAQ extends React.Component<*, void> {
  props: {
    FAQVisibility: Map<string, boolean>,
    toggleFAQVisibility: Function
  }

  renderFAQ = ([question, answer]: [string, any]) => {
    const { FAQVisibility, toggleFAQVisibility } = this.props

    return (
      <div className="question" key={question}>
        <div
          className="show-hide-question"
          onClick={toggleFAQVisibility(question)}
        >
          <i className="material-icons">
            {FAQVisibility.get(question) ? "expand_more" : "chevron_right"}
          </i>
          <div>{question}</div>
        </div>
        {FAQVisibility.get(question) ? (
          <div className="answer">{answer}</div>
        ) : null}
      </div>
    )
  }

  render() {
    return (
      <div className="collection-list-content">
        <div className="card centered-content">
          <h2 className="mdc-typography--title">Frequently Asked Questions</h2>
          <div className="frequently-asked-questions">
            {Object.entries(SETTINGS.is_admin ? adminFAQs : viewerFAQs).map(
              this.renderFAQ
            )}
          </div>
        </div>
      </div>
    )
  }
}
