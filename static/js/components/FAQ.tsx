import React from "react"

import { sectionFAQs } from "../data/faqs"

type Props = {
  FAQVisibility: Map<string, boolean>
  // Curried in HelpPage: called with the question, returns the click handler.
  toggleFAQVisibility: (
    question: string
  ) => (e: React.MouseEvent<HTMLDivElement>) => void
}

export default class FAQ extends React.Component<Props> {
  renderSectionFAQ = ([section, faqs]: [
    string,
    { [key: string]: React.ReactNode }
  ]) => {
    return (
      <div className="faq-section" key={section}>
        <h3 className="mdc-typography--subheading">{section}</h3>
        <div className="frequently-asked-questions">
          {Object.entries(faqs).map(this.renderFAQ)}
        </div>
      </div>
    )
  }

  renderFAQ = ([question, answer]: [string, React.ReactNode]) => {
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
          {Object.entries(sectionFAQs).map(this.renderSectionFAQ)}
          <div className="frequently-asked-questions">
            <div className="question">
              <div className="show-hide-question">
                <i className="material-icons" />
                <div>
                  <a className="mdc-list-item mdc-link" href="/terms/">
                    Terms of Service
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }
}
