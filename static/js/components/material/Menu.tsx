import React from "react"

import { MDCMenu } from "@material/menu/dist/mdc.menu"

import type { MenuItem } from "../../types/uiTypes"

/*
 * @material/menu 0.33 ships no type declarations, so the instance is typed by
 * the three members this component actually uses of it. `open` is a real
 * get/set accessor on MDCMenu.prototype (see @material/menu's index.js), which
 * is what componentDidUpdate assigns to below and what Menu_test.js spies on.
 */
type MDCMenuInstance = {
  open: boolean
  listen: (eventName: string, handler: (event: Event) => void) => void
  destroy: () => void
}

type MenuProps = {
  open: boolean
  showMenu: (event: React.MouseEvent<HTMLAnchorElement>) => void
  closeMenu: () => void
  menuItems: Array<MenuItem>
}

export default class Menu extends React.Component<MenuProps> {
  menu: MDCMenuInstance | null
  menuRoot: HTMLElement | null

  componentDidMount() {
    const { closeMenu } = this.props
    this.menu = new MDCMenu(this.menuRoot)
    if (closeMenu) {
      this.menu && this.menu.listen("MDCMenu:cancel", closeMenu)
      this.menu && this.menu.listen("MDCMenu:selected", closeMenu)
    }
  }

  componentDidUpdate(prevProps: MenuProps) {
    if (this.menu) {
      if (prevProps.open !== this.props.open) {
        this.menu.open = this.props.open
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
          tabIndex={-1}
          ref={div => {
            this.menuRoot = div
          }}
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
