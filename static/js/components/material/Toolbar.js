// @flow
import React from "react"
import { MDCToolbar } from "@material/toolbar/dist/mdc.toolbar"

export default class Toolbar extends React.Component {
  toolbar: null
  toolbarRoot: null

  props: {
    onClickMenu: () => void,
    children: React.Children
  }

  componentDidMount() {
    this.toolbar = new MDCToolbar(this.toolbarRoot)
  }

  componentWillUnmount() {
    if (this.toolbar) {
      this.toolbar.destroy()
    }
  }

  toggleMenu = (event: Event) => {
    const { onClickMenu } = this.props
    event.preventDefault()

    onClickMenu()
  }

  render() {
    const { children } = this.props

    return (
      <header className="mdc-toolbar" ref={div => (this.toolbarRoot = div)}>
        <div className="mdc-toolbar__row">
          <section className="mdc-toolbar__section mdc-toolbar__section--align-start">
            <a
              href="#"
              className="material-icons mdc-toolbar__icon--menu menu-button"
              onClick={this.toggleMenu}
            >
              menu
            </a>
            <span className="mdc-toolbar__title">{children}</span>
          </section>
        </div>
      </header>
    )
  }
}
