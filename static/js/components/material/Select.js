// @flow
import React from "react"

import {MDCSelect} from "@material/select/dist/mdc.select"

export default class Select extends React.Component<*, void> {
  select: null
  selectRoot: ?HTMLElement

  componentDidMount() {
    const { setSelectedEndpoint, selectedEndpoint } = this.props
    this.select = new MDCSelect(this.selectRoot)
    this.select.listen('MDCSelect:change', () => {
      setSelectedEndpoint(this.select.value)
    })
    if (selectedEndpoint) {
      this.select.value = selectedEndpoint
    }
  }

  componentWillUnmount() {
    if (this.select) {
      this.select.destroy()
    }
  }

  render() {
    const { menuItems } = this.props
    let isSelected = false
    if (this.select) {
      isSelected = this.select.selectedIndex > 1
    }

    return (
      <div className="mdc-select mdc-select--box" role="listbox" ref={div => (this.selectRoot = div)}>
        <div className="mdc-select__surface" tabIndex="0">
          <div className={`mdc-select__label ${isSelected ? "mdc-select__label--float-above" : ""}`}>
            Select Edx Endpoint
          </div>
          <div className="mdc-select__selected-text"></div>
          <div className="mdc-select__bottom-line"></div>
        </div>
        <div className="mdc-menu mdc-select__menu">
          <ul className="mdc-list mdc-menu__items">
            {menuItems.map(
              item => (
                <li
                  key={`${item.id}_item`}
                  className="mdc-list-item"
                  role="option"
                  tabIndex="0"
                >
                  {item.name}
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
