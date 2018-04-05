// @flow
import React from "react"

import { MDCMenu } from "@material/menu/dist/mdc.menu"

import type { MenuItem } from "../../flow/uiTypes"

type MenuProps = {
  open: boolean,
  showMenu: Function,
  closeMenu: Function,
  menuItems: Array<MenuItem>
}

export default class Menu extends React.Component<*, void> {
  menu: null
  menuRoot: ?HTMLElement

  componentDidMount() {
    const { closeMenu } = this.props
    this.menu = new MDCMenu(this.menuRoot)
    if (closeMenu) {
      this.menu && this.menu.listen("MDCMenu:cancel", closeMenu)
      this.menu && this.menu.listen("MDCMenu:selected", closeMenu)
    }
  }

  componentWillReceiveProps(nextProps: MenuProps) {
    if (this.menu) {
      if (this.props.open !== nextProps.open) {
        this.menu.open = nextProps.open
      }
    }
  }

  componentWillUnmount() {
    if (this.menu) {
      this.menu.destroy()
    }
  }

  render() {
    const { showMenu, menuItems } = this.props

    return (
      <div className="mdc-menu-anchor">
        <a className="material-icons" onClick={showMenu}>
          more_vert
        </a>
        <div
          className="mdc-menu"
          tabIndex="-1"
          ref={div => (this.menuRoot = div)}
        >
          <ul
            className="mdc-menu__items mdc-list"
            role="menu"
            aria-hidden="true"
          >
            {menuItems.map(
              item => (
                <li
                  key={`${item.label}_item`}
                  className="mdc-list-item"
                  role="menuitem"
                  onClick={item.action}
                >
                  {item.label}
                </li>
              ),
              this
            )}
          </ul>
        </div>
      </div>
    )
  }
}
