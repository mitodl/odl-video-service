import type { SinonStub, SinonSpy } from "sinon"

/*
 * View a stubbed callback prop as the sinon stub it actually is.
 *
 * A component's Props type declares its callbacks by call signature, which is
 * exactly right for the component -- it calls them, it does not inspect them.
 * A test that stubs one and then asserts on sinon's own bookkeeping
 * (callCount, args, returnValues, calledWith) needs the stub view instead.
 *
 * Widening the component's prop type to SinonStub would be wrong: it would let
 * production code reach into stub internals. Casting inline at each of the ~60
 * call sites would be noise that hides what is going on. This names the intent
 * once.
 */
export const asStub = (fn: unknown): SinonStub => fn as unknown as SinonStub

export const asSpy = (fn: unknown): SinonSpy => fn as unknown as SinonSpy

/*
 * querySelector returns Element; RTL's fireEvent and userEvent take
 * HTMLElement. Every element these tests reach for is an HTML element, so the
 * narrowing is safe -- but it has to be stated, and a throw on null is better
 * than a downstream "cannot read property of null".
 */
export const asHTML = (el: Element | null): HTMLElement => {
  if (!el) {
    throw new Error("expected an element, got null")
  }
  return el as HTMLElement
}

/*
 * RTL's queries return HTMLElement, which has no `value`. Every element these
 * tests read a value from is an input or textarea, so the narrowing is safe --
 * but `as HTMLInputElement` scattered inline reads as noise, and this says why.
 */
export const asInput = (el: Element | null): HTMLInputElement =>
  asHTML(el) as HTMLInputElement
