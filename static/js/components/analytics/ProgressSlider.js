import React from "react"

const DEFAULT_HSL = { h: 0, s: 0, l: 0 }

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
    const bgPadding = "30%"
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
            top:             bgPadding,
            right:           0,
            left:            0,
            bottom:          bgPadding,
            backgroundColor: this.hslStr({ ...hsl, l: 25 }),
            opacity:         0.9
          }}
        />
        <span
          className="progress"
          style={{
            position: "absolute",
            top:      0,
            left:     0,
            width:    `${value * 100}%`,
            bottom:   0
          }}
        >
          <span
            className="fill"
            style={{
              position:        "absolute",
              top:             bgPadding,
              bottom:          bgPadding,
              width:           "100%",
              backgroundColor: this.hslStr({ ...hsl, l: 95 }),
              borderColor:     this.hslStr({ ...hsl, l: 5 }),
              borderStyle:     "solid",
              borderWidth:     "1px 0"
            }}
          />
          <span
            className="cursor"
            style={{
              position:        "absolute",
              right:           "-.5em",
              height:          "1em",
              width:           "1em",
              borderRadius:    "50%",
              backgroundColor: this.hslStr({ ...hsl, l: 95 }),
              borderColor:     this.hslStr({ ...hsl, l: 5 }),
              borderWidth:     "1px",
              borderStyle:     "solid"
            }}
          />
        </span>
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
