import React from "react"
import { assert } from "chai"
import { render, screen, fireEvent, cleanup } from "@testing-library/react"

import { makeUnmountRecorder } from "./unmountRecorder"

class Greeter extends React.Component {
  render() {
    return <h1>Hello {this.props.name}</h1>
  }
}

class Counter extends React.Component {
  constructor(props) {
    super(props)
    this.state = { n: 0 }
  }

  render() {
    return (
      <div>
        <span data-testid="n">{String(this.state.n)}</span>
        <button onClick={() => this.setState({ n: this.state.n + 1 })}>
          inc
        </button>
      </div>
    )
  }
}

class AsyncLoader extends React.Component {
  constructor(props) {
    super(props)
    this.state = { value: null }
  }

  componentDidMount() {
    Promise.resolve("loaded").then(value => this.setState({ value }))
  }

  render() {
    return <div>{this.state.value || "loading"}</div>
  }
}

describe("RTL harness", () => {
  it("renders a React 15 class component and queries it by role", () => {
    render(<Greeter name="world" />)
    assert.equal(screen.getByRole("heading").textContent, "Hello world")
  })

  it("exposes the queries the migration depends on", () => {
    render(<Greeter name="again" />)
    assert.isFunction(screen.getByText)
    assert.isFunction(screen.queryByText)
    assert.isFunction(screen.findByText)
    assert.isNotNull(screen.getByText("Hello again"))
  })
})

describe("RTL harness on React 15 without act()", () => {
  it("flushes setState synchronously on fireEvent", () => {
    render(<Counter />)
    fireEvent.click(screen.getByRole("button"))
    assert.equal(screen.getByTestId("n").textContent, "1")
  })

  it("resolves findBy* after an async setState", async () => {
    render(<AsyncLoader />)
    assert.isNotNull(await screen.findByText("loaded"))
  })

  it("fires componentWillUnmount on cleanup()", () => {
    const { UnmountRecorder, getUnmountCount } = makeUnmountRecorder()

    render(<UnmountRecorder />)
    cleanup()
    assert.equal(getUnmountCount(), 1)
  })
})
