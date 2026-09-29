/*
 * casual-browserify ships an index.d.ts, but it declares `module "casual"` --
 * the name of the original package, not this browserify fork -- and has no
 * `types` field in package.json. TypeScript therefore resolves the file, finds
 * no module declaration for the name actually imported, and reports TS2306
 * "File ... is not a module".
 *
 * The shipped file does declare the global `Casual` namespace, so the shapes
 * are reused here rather than restated.
 */
declare module "casual-browserify" {
  const casual: Casual.Generators & Casual.Casual
  export default casual
}
