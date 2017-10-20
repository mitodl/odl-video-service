// @flow
import R from "ramda";

import { S } from "./sanctuary";

// this function checks that a given object passes or fails validation.
// if it fails, it returns a setter (R.set) which which set the appropirate
// validation message in an object. Else, it returns nothing.
//
// The use pattern is to bind the first three arguments, so that the
// validate function (below) can call that bound function with the object
// to validate.
export const validation = R.curry(
  (validator: Function, lens: Function, message: string, toValidate: Object) =>
    validator(R.view(lens, toValidate))
      ? S.Just(R.set(lens, message))
      : S.Nothing
);

// validate takes an array of validations and an object to validate.  A
// validation is a validation function, e.g. as defined above with its first
// three arguments bound (so a validator function, a lens, and a message).
//
// however, any function that takes `toValidate` and returns a setter function
// wrapped in a Just will do.
export const validate = R.curry((validations, toValidate) =>
  R.converge(
    R.compose(R.reduce((acc, setter) => setter(acc), {}), S.justs, Array),
    validations
  )(toValidate)
);

export const emptyOrNil = R.either(R.isEmpty, R.isNil);
