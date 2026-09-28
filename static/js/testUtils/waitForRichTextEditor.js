// @flow
import { assert } from "chai"
import { waitFor, within } from "@testing-library/react"

/*
 * Wait until the RichTextEditor with the given id is usable: its editable
 * region has mounted *and* its formatting toolbar has rendered. Resolves to the
 * editable element.
 *
 * Waiting on `.ProseMirror` alone is not enough. TipTap inserts it
 * synchronously inside createEditor, but the toolbar only renders on the
 * `setState({ lib })` that follows. React 18 batches that update and flushes it
 * later instead of re-rendering inside setState, so an editor-only wait can
 * return in the gap where the field exists and its controls do not - and a test
 * that then reaches for a toolbar button fails intermittently.
 *
 * The gap could be closed in the component with flushSync, but it lasts one
 * render and is invisible to an author, so it is handled here rather than by
 * changing production code for the sake of tests.
 *
 * The toolbar is found from the editor, through the `.rte-frame` they share,
 * so the wait is tied to this editor and not to any toolbar on the page.
 */
export default async function waitForRichTextEditor(
  id: string
): Promise<HTMLElement> {
  let editable
  await waitFor(() => {
    editable = document.querySelector(`#${id} .ProseMirror`)
    assert.isOk(editable, `rich-text editor #${id} never mounted`)
    const frame = editable.closest(".rte-frame")
    assert.isOk(frame, `rich-text editor #${id} is not inside .rte-frame`)
    assert.isOk(
      within(frame).queryByRole("toolbar", { name: "Text formatting" }),
      `toolbar for rich-text editor #${id} never rendered`
    )
  })
  return editable
}
