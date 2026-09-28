import React from "react"
import { render } from "@testing-library/react"
import type { RenderOptions } from "@testing-library/react"
import { Provider } from "react-redux"
import type { Store } from "redux"

/**
 * Render a component tree inside a Redux Provider.
 *
 * Replaces the per-file `renderComponent` helpers that the Enzyme tests each
 * defined locally. Returns RTL's usual result object with `store` added.
 */
type ProviderOptions = RenderOptions & { store?: Store }

export default function renderWithProviders(
  ui: React.ReactElement,
  options: ProviderOptions = {}
) {
  const { store, ...renderOptions } = options

  if (!store) {
    throw new Error("renderWithProviders requires a `store` option")
  }

  const Wrapper = ({ children }: { children?: React.ReactNode }) => (
    <Provider store={store}>{children}</Provider>
  )

  return {
    store,
    ...render(ui, { wrapper: Wrapper, ...renderOptions })
  }
}
