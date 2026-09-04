// @flow
/*
 * Rich-text editor for Collection and Video descriptions.
 *
 * Built on @tiptap/core rather than @tiptap/react: this app is on React 15,
 * which has no hooks, and @tiptap/react needs React >= 17. The core package has
 * no React dependency at all, so RichTextEditor mounts it imperatively against
 * a ref. Nothing here changes when the app moves to React 18.
 *
 * The extension list is explicit rather than StarterKit. That is not for weight
 * (it saves ~3KB) but for correctness: every tag produced here has to survive
 * MIT Learn's `nh3` allowlist, which drops all attributes except href/title and
 * has no heading tags at all. A control that emitted <h2>, an alignment class or
 * a strikethrough would appear to work in OVS and silently lose the formatting
 * on Learn. Keep this list in step with ALLOWED_DESCRIPTION_TAGS in ui/html.py.
 */
import { Editor } from "@tiptap/core"
import Document from "@tiptap/extension-document"
import Paragraph from "@tiptap/extension-paragraph"
import Text from "@tiptap/extension-text"
import Bold from "@tiptap/extension-bold"
import Italic from "@tiptap/extension-italic"
import HardBreak from "@tiptap/extension-hard-break"
import Link from "@tiptap/extension-link"
import Underline from "@tiptap/extension-underline"
import Blockquote from "@tiptap/extension-blockquote"
import { BulletList, OrderedList, ListItem } from "@tiptap/extension-list"
import { UndoRedo } from "@tiptap/extensions"

/*
 * The toolbar, in render order.
 *
 * `icon` is a Material Icons ligature - the same icon set and the same names
 * every word processor uses for these controls, and already loaded app-wide in
 * base.html. `title` is the accessible name and the tooltip. `mark`/`node` name
 * the schema entry a button reflects, so its active state can be read back from
 * the editor.
 */
export const TOOLBAR_BUTTONS = [
  { name: "bold", icon: "format_bold", title: "Bold", mark: "bold" },
  { name: "italic", icon: "format_italic", title: "Italic", mark: "italic" },
  {
    name:  "bulletList",
    icon:  "format_list_bulleted",
    title: "Bulleted list",
    node:  "bulletList"
  },
  {
    name:  "orderedList",
    icon:  "format_list_numbered",
    title: "Numbered list",
    node:  "orderedList"
  },
  { name: "link", icon: "link", title: "Add link", mark: "link" },
  { name: "unlink", icon: "link_off", title: "Remove link", mark: "link" }
]

const EXTENSIONS = [
  Document,
  Paragraph,
  Text,
  Bold,
  Italic,
  HardBreak,
  // openOnClick would navigate away from the form when an author clicks their
  // own link while editing.
  Link.configure({ openOnClick: false, autolink: true }),
  BulletList,
  OrderedList,
  ListItem,
  /*
   * No toolbar button for these two, but they must be loaded: ui/html.py allows
   * <u> and <blockquote>, so without the extensions the schema would drop them
   * on the way in - a description an admin wrote with a blockquote would lose it
   * the next time any author opened the dialog and saved. Loading them makes the
   * allowlist honest, and Mod-U still works for underline.
   */
  Underline,
  Blockquote,
  UndoRedo
]

/*
 * An "empty" TipTap document still serializes to "<p></p>", which would be
 * stored as a non-empty description and render as a stray blank line.
 */
export const normalizeHtml = (html: string): string =>
  html === "<p></p>" || html === "" ? "" : html

/**
 * Create an editor bound to a DOM element.
 *
 * @param element the element to mount into
 * @param content the current description HTML (may be empty)
 * @param onChange called with the serialized HTML on every edit
 */
export const createEditor = (
  element: HTMLElement,
  content: string,
  onChange: (html: string) => void
): Object =>
  new Editor({
    element,
    extensions: EXTENSIONS,
    content:    content || "",
    onUpdate:   ({ editor }) => {
      onChange(normalizeHtml(editor.getHTML()))
    }
  })

/*
 * Only http(s) and mailto links are accepted, matching ALLOWED_URL_SCHEMES in
 * ui/html.py. A bare "learn.mit.edu/x" is treated as https rather than rejected,
 * since that is how authors type URLs.
 */
const SAFE_SCHEME = /^(https?:|mailto:)/i
// host.tld optionally followed by a port, path, query or fragment. Requiring a
// path or end-of-string here rejected `example.com?utm=1`, `example.com#top` and
// `example.com:8080/x`, which authors paste routinely.
const LOOKS_SCHEMELESS = /^[\w-]+(\.[\w-]+)+(:\d+)?([/?#]|$)/

/**
 * Normalize an author-typed link target, or return null if it isn't usable.
 */
export const normalizeHref = (raw: string): ?string => {
  const href = (raw || "").trim()
  if (!href) {
    return null
  }
  if (SAFE_SCHEME.test(href)) {
    return href
  }
  if (LOOKS_SCHEMELESS.test(href)) {
    return `https://${href}`
  }
  return null
}

/**
 * Apply a toolbar button to the editor.
 *
 * Kept next to the button list so the two cannot drift apart. `link` is handled
 * by applyLink instead, because it needs a target from the author first.
 * Returns false when the button did nothing.
 */
export const runCommand = (editor: Object, name: string): boolean => {
  const chain = editor.chain().focus()
  switch (name) {
  case "bold":
    chain.toggleBold().run()
    return true
  case "italic":
    chain.toggleItalic().run()
    return true
  case "bulletList":
    chain.toggleBulletList().run()
    return true
  case "orderedList":
    chain.toggleOrderedList().run()
    return true
  case "unlink":
    chain
      .extendMarkRange("link")
      .unsetLink()
      .run()
    return true
  default:
    return false
  }
}

/**
 * Link the current selection, extending over an existing link if the cursor is
 * inside one. Returns false if the target isn't a usable link.
 */
export const applyLink = (editor: Object, raw: string): boolean => {
  const href = normalizeHref(raw)
  if (!href) {
    return false
  }
  editor
    .chain()
    .focus()
    .extendMarkRange("link")
    .setLink({ href })
    .run()
  return true
}
