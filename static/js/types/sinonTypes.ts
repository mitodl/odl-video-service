import type { SinonSandbox } from "sinon"

// Was an empty object type standing in for sinon's sandbox, which Flow had no
// libdef for. sinon ships its own types, so this is now the real thing.
export type Sandbox = SinonSandbox
