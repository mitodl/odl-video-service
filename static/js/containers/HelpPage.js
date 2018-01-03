// @flow
import React from "react"
import { connect } from "react-redux"
import R from "ramda"

import WithDrawer from "./WithDrawer"
import FAQ from "../components/FAQ"
import { toggleFAQVisibility } from "../actions/commonUi"

class HelpPage extends React.Component {
  toggleShowFAQ = R.curry((questionName, e) => {
    const { dispatch } = this.props

    e.preventDefault()
    dispatch(toggleFAQVisibility(questionName))
  })

  render() {
    const { FAQVisibility } = this.props

    return (
      <WithDrawer>
        <FAQ
          FAQVisibility={FAQVisibility}
          toggleFAQVisibility={this.toggleShowFAQ}
        />
      </WithDrawer>
    )
  }
}

const mapStateToProps = state => ({
  FAQVisibility: state.commonUi.FAQVisibility
})

export default connect(mapStateToProps)(HelpPage)
