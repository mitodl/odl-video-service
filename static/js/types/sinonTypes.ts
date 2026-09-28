// Intentionally empty: the codebase passes a sinon sandbox around but never
// reaches into it through this alias. Replace with sinon's own SinonSandbox
// once @types/sinon is added.
export type Sandbox = Record<string, any>
