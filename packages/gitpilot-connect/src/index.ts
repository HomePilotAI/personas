// packages/gitpilot-connect/src/index.ts
//
// Public surface of @homepilot/gitpilot-connect.
//
// Two import paths are supported:
//
//   import { runWizard, GitPilotClient } from '@homepilot/gitpilot-connect';
//      -> headless API for CLI / scripts
//
//   import { Wizard } from '@homepilot/gitpilot-connect/react';
//      -> React component (lazy; only loads when consumed)
//
// The package is strictly additive: it never reads or writes existing
// HomePilot personas. It only adds new files under
//   ~/.homepilot/connections/<name>.json
// and (when the user opts in at step 6) a new persona file under
//   ~/.homepilot/personas/<slug>.hpersona
//
// See README.md for the architectural overview.

export { GitPilotClient } from './client.js';
export type { ConnectionTestResult } from './client.js';
export {
  WIZARD_STEPS,
  emptyWizardState,
  loadPartial,
  savePartial,
  clearPartial
} from './state.js';
export type { WizardState, WizardStep } from './state.js';
export {
  ConnectionConfigSchema,
  PermissionScopes,
  WorkspaceTargetSchema
} from './types.js';
export type {
  ConnectionConfig,
  PermissionScope,
  WorkspaceTarget
} from './types.js';
export { buildPersonaArtefacts } from './persona-writer.js';
export type { PersonaArtefacts } from './persona-writer.js';
