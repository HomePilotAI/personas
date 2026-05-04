import { afterEach, describe, expect, it } from 'vitest';
import {
  WIZARD_STEPS,
  clearPartial,
  emptyWizardState,
  isFinished,
  loadPartial,
  markStepCompleted,
  nextStep,
  savePartial,
  setStorage
} from '../src/state.js';

function memoryStorage() {
  const map = new Map<string, string>();
  return {
    get: (k: string) => map.get(k) ?? null,
    set: (k: string, v: string) => void map.set(k, v),
    remove: (k: string) => void map.delete(k),
    raw: map
  };
}

describe('wizard state', () => {
  afterEach(() => {
    setStorage(memoryStorage());
    clearPartial();
  });

  it('seeds with safe defaults', () => {
    const s = emptyWizardState();
    expect(s.lastCompleted).toBeNull();
    expect(s.scopes).toEqual(['read']); // mutation OFF by default
    expect(s.enabledTools.length).toBeGreaterThan(0);
    expect(s.endpoint).toContain('mcp-server/mcp');
  });

  it('strips token from disk persistence', () => {
    const store = memoryStorage();
    setStorage(store);
    const s = emptyWizardState();
    s.tokenInMemory = 'super-secret';
    savePartial(s);
    const persisted = JSON.parse(store.raw.get('homepilot.gitpilot.wizard')!);
    expect(persisted.state.tokenInMemory).toBeUndefined();
    expect(JSON.stringify(persisted)).not.toContain('super-secret');
  });

  it('round-trips non-secret state', () => {
    setStorage(memoryStorage());
    const s = emptyWizardState();
    s.lastCompleted = 'endpoint';
    s.endpointVerified = true;
    savePartial(s);
    const back = loadPartial();
    expect(back?.lastCompleted).toBe('endpoint');
    expect(back?.endpointVerified).toBe(true);
  });

  it('returns null when no state on disk', () => {
    setStorage(memoryStorage());
    expect(loadPartial()).toBeNull();
  });

  it('rejects an unsupported version', () => {
    const store = memoryStorage();
    setStorage(store);
    store.raw.set('homepilot.gitpilot.wizard', JSON.stringify({ version: 99, state: {} }));
    expect(loadPartial()).toBeNull();
  });

  it('marks step completed and advances', () => {
    let s = emptyWizardState();
    expect(nextStep(s)).toBe('welcome');
    s = markStepCompleted(s, 'welcome');
    expect(nextStep(s)).toBe('endpoint');
    s = markStepCompleted(s, WIZARD_STEPS[WIZARD_STEPS.length - 1]);
    expect(isFinished(s)).toBe(true);
  });
});
