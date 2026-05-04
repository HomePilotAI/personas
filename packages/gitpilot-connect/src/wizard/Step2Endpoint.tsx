// packages/gitpilot-connect/src/wizard/Step2Endpoint.tsx
import React, { useState } from 'react';
import { GitPilotClient, ConnectionTestResult } from '../client.js';
import { WizardState } from '../state.js';
import { badge, buttonGhost, buttonPrimary, card, helper, input, label, palette } from './styles.js';

export interface Step2Props {
  state: WizardState;
  onChange: (next: Partial<WizardState>) => void;
  onBack: () => void;
  onContinue: () => void;
  fetchImpl?: typeof fetch;
}

export function Step2Endpoint({
  state,
  onChange,
  onBack,
  onContinue,
  fetchImpl
}: Step2Props): React.ReactElement {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<ConnectionTestResult | null>(null);
  const [reveal, setReveal] = useState(false);

  const handleTest = async () => {
    setTesting(true);
    setResult(null);
    try {
      const out = await new GitPilotClient({
        endpoint: state.endpoint,
        token: state.tokenInMemory,
        fetchImpl
      }).test();
      setResult(out);
      onChange({ endpointVerified: out.ok });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div style={card}>
      <h3 style={{ margin: 0, color: palette.text }}>Endpoint &amp; auth</h3>
      <p style={{ color: palette.muted, fontSize: 13 }}>
        The wizard validates the connection before letting you continue.
      </p>

      <div style={{ marginTop: 12 }}>
        <label htmlFor="gp-endpoint" style={label}>
          GitPilot MCP endpoint
        </label>
        <input
          id="gp-endpoint"
          type="url"
          value={state.endpoint}
          onChange={(e) => onChange({ endpoint: e.target.value, endpointVerified: false })}
          style={input}
          placeholder="http://localhost:8000/mcp-server/mcp"
        />
        <div style={helper}>Includes the mount path; the wizard probes /healthz under it.</div>
      </div>

      <div style={{ marginTop: 12 }}>
        <label htmlFor="gp-token" style={label}>
          Bearer token (kept in memory only)
        </label>
        <div style={{ display: 'flex', gap: 6 }}>
          <input
            id="gp-token"
            type={reveal ? 'text' : 'password'}
            value={state.tokenInMemory ?? ''}
            onChange={(e) => onChange({ tokenInMemory: e.target.value, endpointVerified: false })}
            style={input}
            autoComplete="off"
            spellCheck={false}
          />
          <button
            type="button"
            style={buttonGhost}
            onClick={() => setReveal((r) => !r)}
            aria-pressed={reveal}
            title="Toggle reveal"
          >
            {reveal ? 'Hide' : 'Show'}
          </button>
        </div>
        <div style={helper}>
          Never written to disk. Step 7 stores a keychain entry name, not the secret.
        </div>
      </div>

      <div style={{ marginTop: 14, display: 'flex', gap: 8, alignItems: 'center' }}>
        <button
          type="button"
          style={buttonPrimary}
          onClick={handleTest}
          aria-disabled={testing}
        >
          {testing ? 'Testing…' : 'Test connection'}
        </button>
        {result && (
          <span style={badge(result.ok ? 'ok' : 'bad')}>
            {result.ok
              ? `Healthy — ${result.toolCount} tools — ${result.responseTimeMs}ms`
              : `Failed: ${result.error ?? 'unknown error'}`}
          </span>
        )}
      </div>

      <div style={{ marginTop: 16, display: 'flex', gap: 8, justifyContent: 'space-between' }}>
        <button type="button" style={buttonGhost} onClick={onBack}>
          Back
        </button>
        <button
          type="button"
          style={buttonPrimary}
          onClick={onContinue}
          aria-disabled={!state.endpointVerified}
          title={state.endpointVerified ? 'Continue' : 'Run a successful Test connection first'}
        >
          Continue
        </button>
      </div>
    </div>
  );
}
