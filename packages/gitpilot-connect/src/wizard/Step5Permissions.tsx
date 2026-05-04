// packages/gitpilot-connect/src/wizard/Step5Permissions.tsx
import React from 'react';
import { WizardState } from '../state.js';
import { PermissionScope, PermissionScopes } from '../types.js';
import { badge, buttonGhost, buttonPrimary, card, helper, palette } from './styles.js';

export interface Step5Props {
  state: WizardState;
  onChange: (next: Partial<WizardState>) => void;
  onBack: () => void;
  onContinue: () => void;
}

const SCOPE_DESCRIPTIONS: Record<PermissionScope, string> = {
  read: 'List repos, read files, summarise topology. Always allowed.',
  plan: 'Generate plans and dry-run executions. No code is written.',
  mutation: 'Run skills and open pull requests. High-impact — enable consciously.'
};

export function Step5Permissions({
  state,
  onChange,
  onBack,
  onContinue
}: Step5Props): React.ReactElement {
  const toggle = (scope: PermissionScope) => {
    if (scope === 'read') return; // always on
    const has = state.scopes.includes(scope);
    onChange({
      scopes: has
        ? state.scopes.filter((s) => s !== scope)
        : [...state.scopes, scope]
    });
  };

  return (
    <div style={card}>
      <h3 style={{ margin: 0, color: palette.text }}>Permissions</h3>
      <p style={{ color: palette.muted, fontSize: 13 }}>
        Choose which classes of tool the persona may call. You can change this
        later from the same wizard.
      </p>

      <ul role="list" style={{ listStyle: 'none', padding: 0, marginTop: 12 }}>
        {PermissionScopes.map((scope) => {
          const enabled = state.scopes.includes(scope);
          const locked = scope === 'read';
          return (
            <li
              key={scope}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 10,
                padding: '10px 0',
                borderBottom: `1px solid ${palette.border}`
              }}
            >
              <input
                type="checkbox"
                checked={enabled}
                disabled={locked}
                onChange={() => toggle(scope)}
                aria-label={`Enable ${scope}`}
                style={{ marginTop: 4 }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <strong style={{ color: palette.text, textTransform: 'capitalize' }}>{scope}</strong>
                  <span
                    style={badge(
                      scope === 'mutation' ? 'warn' : scope === 'plan' ? 'info' : 'ok'
                    )}
                  >
                    {locked ? 'always on' : enabled ? 'enabled' : 'off'}
                  </span>
                </div>
                <div style={{ color: palette.muted, fontSize: 12 }}>
                  {SCOPE_DESCRIPTIONS[scope]}
                </div>
              </div>
            </li>
          );
        })}
      </ul>

      {state.scopes.includes('mutation') && (
        <div
          role="alert"
          style={{
            ...helper,
            marginTop: 8,
            padding: 8,
            background: palette.warnBg,
            color: palette.warnText,
            borderRadius: 6
          }}
        >
          Mutation tools also require <code>GITPILOT_MCP_SERVER_ALLOW_MUTATION=true</code>{' '}
          and a separate mutation token on the GitPilot side.
        </div>
      )}

      <div style={{ marginTop: 16, display: 'flex', gap: 8, justifyContent: 'space-between' }}>
        <button type="button" style={buttonGhost} onClick={onBack}>
          Back
        </button>
        <button type="button" style={buttonPrimary} onClick={onContinue}>
          Continue
        </button>
      </div>
    </div>
  );
}
