// packages/gitpilot-connect/src/state.ts
//
// Resumable wizard state.
//
// We store the user's in-progress answers between steps so that closing
// the wizard tab or losing the network never costs them their progress.
//
// Storage strategy:
//   * Browser: localStorage under HOMEPILOT_GITPILOT_WIZARD_KEY.
//   * Node (CLI / tests): an in-memory Map. Callers can override via
//     setStorage() to plug in fs or any other backend without bringing
//     a Node-only dependency into the browser bundle.
//
// Secrets handling:
//   * Tokens are NEVER serialised to disk by this module. The state
//     keeps a transient `tokenInMemory` field that is omitted from
//     savePartial(). Persona-writer is the only path that may persist
//     a token, and only via the keychain branch.

import { ConnectionConfig, PermissionScope, WorkspaceTarget } from './types.js';

export const WIZARD_STEPS = [
  'welcome',
  'endpoint',
  'capabilities',
  'workspace',
  'permissions',
  'persona',
  'review'
] as const;
export type WizardStep = (typeof WIZARD_STEPS)[number];

export interface WizardState {
  /** Stable identifier for this wizard run. Generated once, used in logs. */
  wizardId: string;
  /** Last completed step. The current step is the next one in WIZARD_STEPS. */
  lastCompleted: WizardStep | null;
  /** Connection name the user chose (step 7 finalises this). */
  name: string;
  /** Endpoint URL (step 2). */
  endpoint: string;
  /** Whether step 2's connection test succeeded. */
  endpointVerified: boolean;
  /** Tool names ticked at step 3. Defaults to the read-only safe set. */
  enabledTools: string[];
  /** Workspace pin (step 4). */
  workspace: WorkspaceTarget | null;
  /** Scopes (step 5). Mutation OFF by default. */
  scopes: PermissionScope[];
  /** Persona slug to attach to (step 6). */
  personaSlug: string;
  /** Token kept in RAM only — never persisted by savePartial(). */
  tokenInMemory?: string;
}

const STORAGE_KEY = 'homepilot.gitpilot.wizard';
const STORAGE_VERSION = 1;

function newId(): string {
  // crypto.randomUUID is available in browsers (>=Edge 84) and Node 18+.
  // Falls back to a timestamp + random for very old runtimes.
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

export function emptyWizardState(): WizardState {
  return {
    wizardId: newId(),
    lastCompleted: null,
    name: '',
    endpoint: 'http://localhost:8000/mcp-server/mcp',
    endpointVerified: false,
    enabledTools: [
      'gitpilot.healthz',
      'gitpilot.list_repos',
      'gitpilot.list_branches',
      'gitpilot.describe_repo',
      'gitpilot.list_skills',
      'gitpilot.classify_topology'
    ],
    workspace: null,
    scopes: ['read'],
    personaSlug: ''
  };
}

// ---------------------------------------------------------------------------
// Pluggable storage
// ---------------------------------------------------------------------------
export interface Storage {
  get(key: string): string | null;
  set(key: string, value: string): void;
  remove(key: string): void;
}

class MemoryStorage implements Storage {
  private readonly store = new Map<string, string>();
  get(key: string): string | null {
    return this.store.get(key) ?? null;
  }
  set(key: string, value: string): void {
    this.store.set(key, value);
  }
  remove(key: string): void {
    this.store.delete(key);
  }
}

function defaultStorage(): Storage {
  if (typeof globalThis !== 'undefined' && (globalThis as { localStorage?: Storage }).localStorage) {
    return (globalThis as { localStorage: Storage }).localStorage;
  }
  return new MemoryStorage();
}

let storage: Storage = defaultStorage();

export function setStorage(s: Storage): void {
  storage = s;
}

// ---------------------------------------------------------------------------
// Persistence (token-stripped)
// ---------------------------------------------------------------------------
export function savePartial(state: WizardState): void {
  const safe: Omit<WizardState, 'tokenInMemory'> = { ...state };
  delete (safe as Partial<WizardState>).tokenInMemory;
  storage.set(
    STORAGE_KEY,
    JSON.stringify({ version: STORAGE_VERSION, state: safe })
  );
}

export function loadPartial(): WizardState | null {
  const raw = storage.get(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as { version: number; state: WizardState };
    if (parsed.version !== STORAGE_VERSION) return null;
    return parsed.state;
  } catch {
    return null;
  }
}

export function clearPartial(): void {
  storage.remove(STORAGE_KEY);
}

/**
 * Convenience: produce the next state, with `lastCompleted` advanced to
 * the given step. Pure: callers invoke savePartial() themselves so the
 * write moment is explicit.
 */
export function markStepCompleted(
  state: WizardState,
  step: WizardStep
): WizardState {
  return { ...state, lastCompleted: step };
}

export function nextStep(state: WizardState): WizardStep {
  if (state.lastCompleted === null) return WIZARD_STEPS[0];
  const idx = WIZARD_STEPS.indexOf(state.lastCompleted);
  if (idx === -1 || idx + 1 >= WIZARD_STEPS.length) {
    return WIZARD_STEPS[WIZARD_STEPS.length - 1];
  }
  return WIZARD_STEPS[idx + 1];
}

export function isFinished(state: WizardState): boolean {
  return state.lastCompleted === WIZARD_STEPS[WIZARD_STEPS.length - 1];
}
