import React from "react"
import { connect } from "react-redux"
import type { Dispatch } from "redux"
import * as R from "ramda"

import WithDrawer from "./WithDrawer"
import FAQ from "../components/FAQ"
import { toggleFAQVisibility } from "../actions/commonUi"
import type { RootState } from "../types/rootState"

type Props = {
  dispatch: Dispatch
  FAQVisibility: Map<string, boolean>
}

class HelpPage extends React.Component<Props> {
  toggleShowFAQ = R.curry(
    (questionName: string, e: React.MouseEvent<HTMLDivElement>) => {
      const { dispatch } = this.props

      e.preventDefault()
      dispatch(toggleFAQVisibility(questionName))
    }
  )

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

const mapStateToProps = (state: RootState) => ({
  FAQVisibility: state.commonUi.FAQVisibility
})

export default connect(mapStateToProps)(HelpPage)
