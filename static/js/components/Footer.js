// @flow
/* global SETTINGS: false */
import React from "react"
import moment from "moment"

const currentYear = () => moment().format("YYYY")

export default class Footer extends React.Component<*, void> {
  render() {
    return (
      <footer id="footer">
        <div className="container">
          <div className="mdc-layout-grid">
            <div className="mdc-layout-grid__inner">
              <div className="mdc-layout-grid__cell--span-6 mdc-layout-grid__cell--span-12-tablet">
                <a
                  href="http://www.mit.edu"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <img
                    src="/static/images/mit-logo-ltgray-white@72x38.svg"
                    alt="MIT"
                    width="72"
                    height="38"
                  />
                </a>
                <div className="footer-links">
                  <a
                    href="https://openlearning.mit.edu/"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    MIT Open Learning
                  </a>
                  <a href="/terms/" rel="noopener noreferrer">
                    ODL Video Services Terms of Service
                  </a>
                  <a
                    className="contact-us"
                    href={`mailto:${SETTINGS.support_email_address}`}
                  >
                    Contact Us
                  </a>
                </div>
                <address className="footer-address">
                  Massachusetts Institute of Technology
                  <br /> Cambridge, MA 02139
                </address>
              </div>
              <div className="mdc-layout-grid__cell--span-6 mdc-layout-grid__cell--span-12-tablet copyright">
                <div className="footer-copy">
                  &copy; 2016-{currentYear()} Massachusetts Institute of
                  Technology
                </div>
              </div>
            </div>
          </div>
        </div>
      </footer>
    )
  }
}
