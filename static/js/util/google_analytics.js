// @flow
/* global SETTINGS:false */
import ga from "react-ga"
import R from "ramda"

const makeGAEvent = (category, action, label, value) => ({
  category: category,
  action:   action,
  label:    label,
  value:    Math.round(value)
})

const isValidNumber = R.both(R.is(Number), R.complement(R.equals(NaN)))

const removeInvalidValue = R.when(
  R.compose(R.complement(isValidNumber), R.prop("value")),
  R.dissoc("value")
)
const formatGAEvent = R.compose(removeInvalidValue, makeGAEvent)

export const sendGAEvent = (
  category: string,
  action: string,
  label: string,
  value?: number
) => {
  ga.event(formatGAEvent(category, action, label, value))
}

export const sendGAPageView = (page: string) => {
  ga.pageview(page)
}

export const initGA = () => {
  const debug = SETTINGS.reactGaDebug === "true"
  if (SETTINGS.gaTrackingID) {
    ga.initialize(SETTINGS.gaTrackingID, { debug: debug })
  }
}
