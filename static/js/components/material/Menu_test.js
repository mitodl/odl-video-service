// @flow
import React from "react"
import { render } from "@testing-library/react"
import { assert } from "chai"
import sinon from "sinon"

import { MDCMenu } from "@material/menu/dist/mdc.menu"
import Menu from "./Menu"

describe("Menu", () => {
  let sandbox
  const menuItems = [{ label: "Item 1", action: () => {} }]

  beforeEach(() => {
    sandbox = sinon.createSandbox()
  })

  afterEach(() => {
    sandbox.restore()
  })

  const renderMenu = (props = {}) =>
    render(
      <Menu
        open={false}
        showMenu={sinon.stub()}
        closeMenu={sinon.stub()}
        menuItems={menuItems}
        {...props}
      />
    )

  // componentDidUpdate replaced componentWillReceiveProps here. Nothing
  // previously mounted this component and toggled `open`, so a regression
  // in that comparison (e.g. the mdc menu open state getting out of sync
  // after a reopen) would still pass the existing shallow-rendered
  // VideoCard tests.
  //
  // Deviation from the conversion dossier, verified by hand: the dossier
  // proposed reading `mdc-menu--open` off the `.mdc-menu` root via
  // classList, on the claim that MDCMenuFoundation toggles that class
  // synchronously with no rAF gating. That claim is false for Menu
  // specifically (it holds for Drawer and Dialog, confirmed empirically
  // when converting those two files). Reading node_modules/@material/menu/
  // foundation.js directly: both open() and close() add the OPEN class only
  // *inside* a requestAnimationFrame callback -- `isOpen_` itself is set
  // synchronously, but the DOM class is not. Worse, this suite's
  // global_init.js stubs `requestAnimationFrame` to `() => null` and never
  // invokes the callback at all (a workaround for MDC/HTMLCanvasElement),
  // so `mdc-menu--open` is never added to the DOM under test, no matter how
  // long a test waits -- confirmed by dumping the rendered HTML after
  // toggling `open` and seeing only the (synchronously-added)
  // `mdc-menu--animating-open` class appear, never `mdc-menu--open`. A
  // classList assertion on `mdc-menu--open` would therefore silently prove
  // nothing (or always fail), regardless of the real prop-toggle behavior.
  //
  // Working alternative: `MDCMenu.prototype.open` is a real get/set
  // accessor (see @material/menu's index.js) that Menu.js's
  // componentDidUpdate invokes via `this.menu.open = this.props.open`.
  // Spying on that accessor's setter observes the exact call this test
  // cares about without touching production code, without `.instance()`,
  // and without depending on the broken rAF-gated DOM class. It is the same
  // "spy a prototype method installed pre-mount" idiom used for
  // Dialog.prototype.showMdc/destroyMdc, applied to a third-party
  // prototype's accessor instead of an own-class method -- verified working
  // via an empirical throwaway probe before writing this.
  it("tracks the open prop on the underlying MDC menu across toggles, including a reopen", () => {
    const openSpy = sandbox.spy(MDCMenu.prototype, "open", ["set"])
    const { rerender } = renderMenu({ open: false })
    assert.equal(openSpy.set.callCount, 0)

    rerender(
      <Menu
        open={true}
        showMenu={sinon.stub()}
        closeMenu={sinon.stub()}
        menuItems={menuItems}
      />
    )
    sinon.assert.calledOnce(openSpy.set)
    assert.isTrue(openSpy.set.lastCall.args[0])

    rerender(
      <Menu
        open={false}
        showMenu={sinon.stub()}
        closeMenu={sinon.stub()}
        menuItems={menuItems}
      />
    )
    sinon.assert.calledTwice(openSpy.set)
    assert.isFalse(openSpy.set.lastCall.args[0])

    rerender(
      <Menu
        open={true}
        showMenu={sinon.stub()}
        closeMenu={sinon.stub()}
        menuItems={menuItems}
      />
    )
    sinon.assert.calledThrice(openSpy.set)
    assert.isTrue(openSpy.set.lastCall.args[0])
  })

  // The original assertion here is `instance.menu` object identity -- did
  // componentDidMount's `new MDCMenu()` call re-run -- which has no direct
  // RTL equivalent (no `.instance()`, and MDCMenu is a third-party value
  // import, not a project-owned module whose constructor is safe to stub
  // the way VideoPlayer_test.js stubs `libVideo.videojs`). A DOM-node-identity
  // proxy (asserting `.mdc-menu` is the same node before/after rerender) was
  // tried and rejected: it only detects a full React unmount/remount, so it
  // stays green even when componentDidUpdate spuriously reruns
  // `new MDCMenu(this.menuRoot)` against the *same*, still-mounted node --
  // exactly the regression this test exists to catch.
  //
  // Instead this spies `MDCMenu.prototype.initialSyncWithDOM`, the method
  // `MDCComponent`'s base constructor always invokes as its last step (see
  // node_modules/@material/base/component.js). MDCMenu does not override
  // `initialSyncWithDOM` itself, so it is inherited from `MDCComponent`, but
  // sinon still intercepts it correctly by defining a shadowing own property
  // on `MDCMenu.prototype` -- confirmed empirically before writing this.
  // Counting its calls is a direct proxy for "how many times was `new
  // MDCMenu()` constructed", stronger than the object-identity check it
  // replaces: it fails if construction re-runs even against the same DOM
  // node. Paired with asserting the open-accessor setter was never called
  // (a more direct, spy-based substitute for the original's
  // `assert.isFalse(instance.menu.open)` -- see the rAF note on the test
  // above for why reading the `mdc-menu--open` class itself would not work
  // here), this covers both halves of the original assertion.
  it("does not touch the MDC menu when an unrelated prop changes", () => {
    const constructSpy = sandbox.spy(MDCMenu.prototype, "initialSyncWithDOM")
    const openSpy = sandbox.spy(MDCMenu.prototype, "open", ["set"])
    const { rerender } = renderMenu({ open: false })
    sinon.assert.calledOnce(constructSpy)

    rerender(
      <Menu
        open={false}
        showMenu={sinon.stub()}
        closeMenu={sinon.stub()}
        menuItems={[{ label: "Item 2", action: () => {} }]}
      />
    )

    sinon.assert.calledOnce(constructSpy)
    sinon.assert.notCalled(openSpy.set)
  })
})
