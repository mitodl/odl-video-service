import React from "react"

const DEFAULT_HSL = { h: 0, s: 0, l: 50 }

class ProgressSlider extends React.Component {
  render() {
    const { hsl, value, ...passThroughProps } = {
      hsl: DEFAULT_HSL,
      ...this.props
    }
    const style = Object.assign({}, passThroughProps.style, {
      height: "1em",
      hsl,
      cursor: "pointer"
    })
    return (
      <div
        ref={ref => {
          this.rootRef = ref
        }}
        className="time-slider"
        {...passThroughProps}
        style={style}
        onClick={this.onClickSlider.bind(this)}
      >
        <span
          className="background"
          style={{
            position:        "absolute",
            top:             0,
            right:           0,
            left:            0,
            bottom:          0,
            backgroundColor: this.hslStr(hsl),
            opacity:         0.4
          }}
        />
        <span
          className="progress"
          style={{
            position:        "absolute",
            top:             0,
            left:            0,
            width:           `${value * 100}%`,
            bottom:          0,
            backgroundColor: this.hslStr(hsl),
            borderRight:     `.4em solid ${this.hslStr({ ...hsl, l: hsl.l / 2 })}`
          }}
        />
      </div>
    )
  }

  onClickSlider(event) {
    const bounds = this.getBounds()
    const xOffset = event.pageX - bounds.x
    const xPercent = xOffset / bounds.width
    if (this.props.onChange) {
      this.props.onChange(xPercent)
    }
  }

  getBounds() {
    return this.rootRef.getBoundingClientRect()
  }

  hslStr(hsl = {}) {
    return `hsl(${hsl.h}, ${hsl.s}%, ${hsl.l}%)`
  }
}

export default ProgressSlider
