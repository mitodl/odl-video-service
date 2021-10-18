// @flow
import React from "react"

import { MDCSelect } from "@material/select/dist/mdc.select"
import type { MenuItem } from "../../flow/uiTypes"

type SelectProps = {
  open: boolean,
  selectedEndpoint: number,
  menuItems: Array<MenuItem>
}

export default class Select extends React.Component<*, void> {
  select: null
  selectRoot: ?HTMLElement

  componentDidMount() {
    const { setSelectedEndpoint } = this.props
    this.select = new MDCSelect(this.selectRoot)
    this.select.listen("MDCSelect:change", () => {
      if (this.select) {
        setSelectedEndpoint(this.select.value)
      }
    })
  }
  // eslint-disable-next-line react/no-deprecated
  componentWillReceiveProps(nextProps: SelectProps) {
    if (this.select && nextProps.selectedEndpoint) {
      if (this.select.selectedIndex < 0) {
        this.select.selectedIndex = nextProps.selectedEndpoint
      }
    }
  }

  componentWillUnmount() {
    if (this.select) {
      this.select.destroy()
    }
  }

  render() {
    const { menuItems, selectedEndpoint } = this.props
    const isSelected = selectedEndpoint !== null

    return (
      <div
        className="mdc-select mdc-select--box"
        role="listbox"
        ref={div => (this.selectRoot = div)}
      >
        <div className="mdc-select__surface" tabIndex="0">
          <div
            className={`mdc-select__label ${
              isSelected ? "mdc-select__label--float-above" : ""
            }`}
          >
            Select Edx Endpoint
          </div>
          <div className="mdc-select__selected-text" />
          <div className="mdc-select__bottom-line" />
        </div>
        <div className="mdc-menu mdc-select__menu">
          <ul className="mdc-list mdc-menu__items">
            {menuItems.map(
              item => (
                <li
                  key={`${item.id}_item`}
                  className="mdc-list-item"
                  aria-selected={
                    selectedEndpoint && item.id === selectedEndpoint
                  }
                  role="option"
                  tabIndex="0"
                  id={item.id}
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
