// @flow
import { assert } from "chai"

import { calculateListPermissionValue, wait } from "./util"

describe("util functions", () => {
  it("waits some milliseconds", done => {
    let executed = false
    wait(30).then(() => {
      executed = true
    })

    setTimeout(() => {
      assert.isFalse(executed)

      setTimeout(() => {
        assert.isTrue(executed)

        done()
      }, 20)
    }, 20)
  })
  it("test moira list values", () => {
    const moiraString = ",foo,,,bar,rab,oof,"
    const expectedLists = ["foo", "bar", "rab", "oof"]
    assert.deepEqual(
      expectedLists,
      calculateListPermissionValue("lists", moiraString)
    )
  })
})
