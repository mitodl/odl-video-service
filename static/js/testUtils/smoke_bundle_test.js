import { assert } from "chai"
import { bootBundle, bundleIsBuilt } from "../../../scripts/test/smoke_bundle"

describe("production bundle smoke test", function() {
  // Booting the whole app bundle is far slower than a unit test.
  this.timeout(60000)

  it("boots and mounts React into #container", function() {
    if (!bundleIsBuilt()) {
      this.skip()
      return
    }

    const { container, errors } = bootBundle()

    assert.deepEqual(
      errors,
      [],
      `bundle threw during boot: ${errors.join("; ")}`
    )
    assert.isAbove(
      container.childNodes.length,
      0,
      "React did not mount anything into #container"
    )
  })
})
