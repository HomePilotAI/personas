// packages/gitpilot-connect/src/wizard/Step1Welcome.tsx
import React, { useEffect, useState } from 'react';
import { GitPilotClient } from '../client.js';
import { WizardState } from '../state.js';
import { badge, buttonGhost, buttonPrimary, card, palette } from './styles.js';

export interface Step1Props {
  state: WizardState;
  onContinue: () => void;
  onCancel: () => void;
  fetchImpl?: typeof fetch;
}

export function Step1Welcome({ state, onContinue, onCancel, fetchImpl }: Step1Props): React.ReactElement {
  const [reachable, setReachable] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [detail, setDetail] = useState<string>('');

  useEffect(() => {
    let cancelled = false;
    setBusy(true);
    void new GitPilotClient({ endpoint: state.endpoint, fetchImpl })
      .test()
      .then((res) => {
        if (cancelled) return;
        setReachable(res.reachable);
        setDetail(
          res.reachable
            ? `Server alive (${res.toolCount} tools, ${res.responseTimeMs}ms)`
            : (res.error ?? 'No response')
        );
      })
      .catch((e) => {
        if (cancelled) return;
        setReachable(false);
        setDetail(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [state.endpoint, fetchImpl]);

  return (
    <div style={card}>
      <h3 style={{ margin: 0, color: palette.text }}>Connect HomePilot to GitPilot</h3>
      <p style={{ color: palette.muted, fontSize: 13 }}>
        Seven steps. Resumable. Strictly additive — nothing existing in your
        HomePilot install will be modified.
      </p>

      <div style={{ marginTop: 12 }}>
        <strong style={{ color: palette.text, fontSize: 13 }}>Prerequisites</strong>
        <ul style={{ color: palette.muted, fontSize: 13, marginTop: 8 }}>
          <li>
            GitPilot is running with <code>GITPILOT_EXPOSE_MCP_SERVER=true</code>.
          </li>
          <li>
            You have a bearer token (the value of{' '}
            <code>GITPILOT_MCP_SERVER_TOKEN</code>).
          </li>
          <li>You can reach the GitPilot endpoint over HTTP(S).</li>
        </ul>
      </div>

      <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={badge(reachable === null ? 'info' : reachable ? 'ok' : 'bad')}>
          {busy ? 'Probing…' : reachable === null ? 'Idle' : reachable ? 'Reachable' : 'Unreachable'}
        </span>
        <span style={{ color: palette.muted, fontSize: 12 }}>{detail}</span>
      </div>

      <div style={{ marginTop: 16, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button type="button" style={buttonGhost} onClick={onCancel}>
          Cancel
        </button>
        <button
          type="button"
          style={buttonPrimary}
          onClick={onContinue}
          aria-disabled={busy}
        >
          Continue
        </button>
      </div>
    </div>
  );
}
