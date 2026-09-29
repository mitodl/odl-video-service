import React from "react"
import type { ReactNode } from "react"
import { MDCToolbar } from "@material/toolbar/dist/mdc.toolbar"

/*
 * @material/toolbar 0.33 ships no type declarations, so the instance is typed
 * by the one member this component actually uses of it.
 */
type MDCToolbarInstance = {
  destroy: () => void
}

type Props = {
  onClickMenu: () => void
  children: ReactNode
}

export default class Toolbar extends React.Component<Props> {
  toolbar: MDCToolbarInstance | null
  toolbarRoot: HTMLElement | null

  componentDidMount() {
    this.toolbar = new MDCToolbar(this.toolbarRoot)
  }

  componentWillUnmount() {
    if (this.toolbar) {
      this.toolbar.destroy()
    }
  }

  toggleMenu = (event: React.MouseEvent<HTMLAnchorElement>) => {
    const { onClickMenu } = this.props
    event.preventDefault()

    onClickMenu()
  }

  render() {
    const { children } = this.props

    return (
      <header
        className="mdc-toolbar"
        ref={div => {
          this.toolbarRoot = div
        }}
      >
        <div className="mdc-toolbar__row">
          <section className="mdc-toolbar__section mdc-toolbar__section--align-start">
            <a
              href="#"
              className="material-icons mdc-toolbar__menu-icon menu-button"
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
