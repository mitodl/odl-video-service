// @flow
import React from "react"
import moment from "moment"

const currentYear = () => moment().format("YYYY")

export default class Footer extends React.Component {
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
                    href="https://odl.mit.edu/"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Office of Digital Learning
                  </a>
                </div>
                <address className="footer-address">
                  Massachusetts Institute of Technology<br /> Cambridge, MA
                  02139
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
