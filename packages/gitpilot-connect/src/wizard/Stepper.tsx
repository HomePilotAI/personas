// packages/gitpilot-connect/src/wizard/Stepper.tsx
//
// Visual stepper at the top of the wizard. Pure presentational; the
// active step + completed flags are computed by the parent.

import React from 'react';
import { WIZARD_STEPS, WizardStep } from '../state.js';
import { palette } from './styles.js';

const HUMAN: Record<WizardStep, string> = {
  welcome: 'Welcome',
  endpoint: 'Endpoint',
  capabilities: 'Capabilities',
  workspace: 'Workspace',
  permissions: 'Permissions',
  persona: 'Persona',
  review: 'Review'
};

export interface StepperProps {
  current: WizardStep;
  lastCompleted: WizardStep | null;
  onJumpTo?: (step: WizardStep) => void;
}

export function Stepper({ current, lastCompleted, onJumpTo }: StepperProps): React.ReactElement {
  const completedIdx =
    lastCompleted === null ? -1 : WIZARD_STEPS.indexOf(lastCompleted);

  return (
    <ol
      role="list"
      aria-label="Wizard progress"
      style={{
        display: 'flex',
        gap: 8,
        margin: 0,
        padding: 0,
        listStyle: 'none',
        flexWrap: 'wrap'
      }}
    >
      {WIZARD_STEPS.map((step, idx) => {
        const isCurrent = step === current;
        const isDone = idx <= completedIdx;
        const navigable = isDone || idx === completedIdx + 1;

        const bg = isCurrent ? palette.accentSoft : palette.surface;
        const color = isCurrent
          ? palette.accentText
          : isDone
            ? palette.okText
            : palette.muted;

        return (
          <li key={step} style={{ flex: '0 0 auto' }}>
            <button
              type="button"
              aria-current={isCurrent ? 'step' : undefined}
              disabled={!navigable || !onJumpTo}
              onClick={() => onJumpTo && navigable && onJumpTo(step)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 10px',
                background: bg,
                color,
                border: `1px solid ${isCurrent ? palette.accent : palette.border}`,
                borderRadius: 6,
                fontSize: 12,
                cursor: navigable && onJumpTo ? 'pointer' : 'default'
              }}
            >
              <span
                aria-hidden
                style={{
                  width: 18,
                  height: 18,
                  borderRadius: '50%',
                  background: isDone
                    ? palette.ok
                    : isCurrent
                      ? palette.accent
                      : palette.border,
                  color: '#fff',
                  fontSize: 11,
                  fontWeight: 700,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                {isDone ? '✓' : idx + 1}
              </span>
              {HUMAN[step]}
            </button>
          </li>
        );
      })}
    </ol>
  );
}
