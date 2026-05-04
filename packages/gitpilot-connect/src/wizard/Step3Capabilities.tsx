// packages/gitpilot-connect/src/wizard/Step3Capabilities.tsx
import React, { useEffect, useState } from 'react';
import { GitPilotClient } from '../client.js';
import { WizardState } from '../state.js';
import { badge, buttonGhost, buttonPrimary, card, helper, palette } from './styles.js';

interface ToolDef {
  name: string;
  description?: string;
  scope?: string;
}

export interface Step3Props {
  state: WizardState;
  onChange: (next: Partial<WizardState>) => void;
  onBack: () => void;
  onContinue: () => void;
  fetchImpl?: typeof fetch;
}

export function Step3Capabilities({
  state,
  onChange,
  onBack,
  onContinue,
  fetchImpl
}: Step3Props): React.ReactElement {
  const [tools, setTools] = useState<ToolDef[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void new GitPilotClient({ endpoint: state.endpoint, fetchImpl })
      .listTools()
      .then((list) => {
        if (cancelled) return;
        setTools(list);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [state.endpoint, fetchImpl]);

  const toggle = (name: string) => {
    const enabled = state.enabledTools.includes(name);
    onChange({
      enabledTools: enabled
        ? state.enabledTools.filter((n) => n !== name)
        : [...state.enabledTools, name]
    });
  };

  return (
    <div style={card}>
      <h3 style={{ margin: 0, color: palette.text }}>Capability preview</h3>
      <p style={{ color: palette.muted, fontSize: 13 }}>
        Tick the tools your Coder persona may call. Mutation tools (orange)
        require explicit scope at step 5.
      </p>

      {loading && <div style={helper}>Loading tools…</div>}
      {error && <div style={badge('bad')}>{error}</div>}

      {!loading && !error && (
        <ul role="list" style={{ listStyle: 'none', margin: '12px 0 0', padding: 0 }}>
          {tools.map((tool) => {
            const enabled = state.enabledTools.includes(tool.name);
            const scope = (tool.scope ?? 'read') as 'read' | 'plan' | 'mutation';
            const scopeKind = scope === 'mutation' ? 'warn' : scope === 'plan' ? 'info' : 'ok';
            return (
              <li
                key={tool.name}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 10,
                  padding: '8px 0',
                  borderBottom: `1px solid ${palette.border}`
                }}
              >
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={() => toggle(tool.name)}
                  aria-label={`Enable ${tool.name}`}
                  style={{ marginTop: 4 }}
                />
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      display: 'flex',
                      gap: 6,
                      alignItems: 'center'
                    }}
                  >
                    <code style={{ color: palette.text, fontSize: 13 }}>{tool.name}</code>
                    <span style={badge(scopeKind)}>{scope}</span>
                  </div>
                  {tool.description && (
                    <div style={{ color: palette.muted, fontSize: 12 }}>{tool.description}</div>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <div style={{ marginTop: 16, display: 'flex', gap: 8, justifyContent: 'space-between' }}>
        <button type="button" style={buttonGhost} onClick={onBack}>
          Back
        </button>
        <button
          type="button"
          style={buttonPrimary}
          onClick={onContinue}
          aria-disabled={state.enabledTools.length === 0}
        >
          Continue
        </button>
      </div>
    </div>
  );
}
