// packages/gitpilot-connect/src/wizard/Wizard.tsx
//
// Top-level wizard component. Orchestrates step navigation and
// auto-saves partial state to localStorage on every change.
//
// Best-practice contract:
//   * Resumable: opens at the next step after lastCompleted.
//   * Diff-before-write: step 7 shows JSON; the actual write is the
//     consumer's responsibility (we just pass artefacts to onComplete).
//   * Tokens never leave RAM — savePartial() strips tokenInMemory.
//   * Idempotent: re-running for an existing connection name produces
//     the same artefacts (verified by manifestHash).

import React, { useEffect, useState } from 'react';
import {
  WizardState,
  WIZARD_STEPS,
  WizardStep,
  emptyWizardState,
  loadPartial,
  markStepCompleted,
  nextStep,
  savePartial,
  clearPartial
} from '../state.js';
import { PersonaArtefacts } from '../persona-writer.js';
import { ConnectionConfig } from '../types.js';
import { Stepper } from './Stepper.js';
import { Step1Welcome } from './Step1Welcome.js';
import { Step2Endpoint } from './Step2Endpoint.js';
import { Step3Capabilities } from './Step3Capabilities.js';
import { Step4Workspace } from './Step4Workspace.js';
import { Step5Permissions } from './Step5Permissions.js';
import { Step6Persona } from './Step6Persona.js';
import { Step7Review } from './Step7Review.js';
import { palette } from './styles.js';

export interface WizardProps {
  /** Called after step 7. Caller writes the artefacts to disk. */
  onComplete: (artefacts: PersonaArtefacts, config: ConnectionConfig) => void;
  /** Called if the user abandons the wizard. State is preserved on disk. */
  onCancel: () => void;
  /** Optional pre-populated existing personas list for step 6. */
  existingPersonas?: { slug: string; name: string }[];
  /** Test seam: override fetch. */
  fetchImpl?: typeof fetch;
}

export function Wizard({ onComplete, onCancel, existingPersonas, fetchImpl }: WizardProps): React.ReactElement {
  const [state, setState] = useState<WizardState>(() => loadPartial() ?? emptyWizardState());
  const current: WizardStep =
    state.lastCompleted === null ? 'welcome' : nextStep(state);

  useEffect(() => {
    savePartial(state);
  }, [state]);

  const update = (partial: Partial<WizardState>) =>
    setState((s) => ({ ...s, ...partial }));
  const advance = (step: WizardStep) =>
    setState((s) => markStepCompleted(s, step));
  const back = () => {
    const idx = WIZARD_STEPS.indexOf(current);
    if (idx <= 0) return;
    setState((s) => ({
      ...s,
      lastCompleted: idx <= 1 ? null : WIZARD_STEPS[idx - 2]
    }));
  };
  const jumpTo = (step: WizardStep) => {
    const idx = WIZARD_STEPS.indexOf(step);
    if (idx <= 0) {
      setState((s) => ({ ...s, lastCompleted: null }));
    } else {
      setState((s) => ({ ...s, lastCompleted: WIZARD_STEPS[idx - 1] }));
    }
  };

  const handleFinish = (artefacts: PersonaArtefacts, config: ConnectionConfig) => {
    advance('review');
    clearPartial();
    onComplete(artefacts, config);
  };

  return (
    <section
      aria-labelledby="gp-wizard-title"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
        background: palette.bg,
        color: palette.text,
        padding: 16,
        borderRadius: 10,
        maxWidth: 720
      }}
    >
      <h2 id="gp-wizard-title" style={{ margin: 0, fontSize: 18 }}>
        Connect GitPilot
      </h2>
      <Stepper current={current} lastCompleted={state.lastCompleted} onJumpTo={jumpTo} />

      {current === 'welcome' && (
        <Step1Welcome
          state={state}
          fetchImpl={fetchImpl}
          onContinue={() => advance('welcome')}
          onCancel={onCancel}
        />
      )}
      {current === 'endpoint' && (
        <Step2Endpoint
          state={state}
          fetchImpl={fetchImpl}
          onChange={update}
          onBack={back}
          onContinue={() => advance('endpoint')}
        />
      )}
      {current === 'capabilities' && (
        <Step3Capabilities
          state={state}
          fetchImpl={fetchImpl}
          onChange={update}
          onBack={back}
          onContinue={() => advance('capabilities')}
        />
      )}
      {current === 'workspace' && (
        <Step4Workspace
          state={state}
          fetchImpl={fetchImpl}
          onChange={update}
          onBack={back}
          onContinue={() => advance('workspace')}
        />
      )}
      {current === 'permissions' && (
        <Step5Permissions
          state={state}
          onChange={update}
          onBack={back}
          onContinue={() => advance('permissions')}
        />
      )}
      {current === 'persona' && (
        <Step6Persona
          state={state}
          existingPersonas={existingPersonas}
          onChange={update}
          onBack={back}
          onContinue={() => advance('persona')}
        />
      )}
      {current === 'review' && (
        <Step7Review state={state} onBack={back} onSave={handleFinish} />
      )}
    </section>
  );
}
