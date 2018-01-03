// @flow
import React from "react"

import { MDCSimpleMenu } from "@material/menu/dist/mdc.menu"

import type { MenuItem } from "../../flow/uiTypes"

type MenuProps = {
  open: boolean,
  showMenu: Function,
  closeMenu: Function,
  menuItems: Array<MenuItem>
}

export default class Menu extends React.Component {
  menu: null
  menuRoot: null

  componentDidMount() {
    const { closeMenu } = this.props
    this.menu = new MDCSimpleMenu(this.menuRoot)
    if (closeMenu) {
      this.menu.listen("MDCSimpleMenu:cancel", closeMenu)
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
          className="mdc-simple-menu"
          tabIndex="-1"
          ref={div => (this.menuRoot = div)}
        >
          <ul
            className="mdc-simple-menu__items mdc-list"
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
