// packages/gitpilot-connect/src/wizard/Step7Review.tsx
import React, { useMemo } from 'react';
import { buildPersonaArtefacts, PersonaArtefacts } from '../persona-writer.js';
import { WizardState } from '../state.js';
import { ConnectionConfig } from '../types.js';
import { buttonGhost, buttonPrimary, card, helper, palette } from './styles.js';

export interface Step7Props {
  state: WizardState;
  onBack: () => void;
  onSave: (artefacts: PersonaArtefacts, config: ConnectionConfig) => void;
}

function toConfig(state: WizardState): ConnectionConfig | null {
  if (!state.workspace) return null;
  return {
    name: state.name || (state.personaSlug.replace(/^coder-/, '') || 'gitpilot'),
    endpoint: state.endpoint,
    auth: state.tokenInMemory
      ? { source: 'inline', token: state.tokenInMemory }
      : { source: 'keychain', entryName: 'gitpilot-token' },
    enabledTools: state.enabledTools,
    scopes: state.scopes,
    workspace: state.workspace,
    verifiedAt: state.endpointVerified ? new Date().toISOString() : undefined
  };
}

export function Step7Review({ state, onBack, onSave }: Step7Props): React.ReactElement {
  const config = useMemo(() => toConfig(state), [state]);
  const artefacts = useMemo(
    () => (config ? buildPersonaArtefacts({ config }) : null),
    [config]
  );

  if (!config || !artefacts) {
    return (
      <div style={card}>
        <p style={helper}>Wizard state incomplete; please go back and fix the highlighted steps.</p>
        <button type="button" style={buttonGhost} onClick={onBack}>
          Back
        </button>
      </div>
    );
  }

  return (
    <div style={card}>
      <h3 style={{ margin: 0, color: palette.text }}>Review &amp; save</h3>
      <p style={{ color: palette.muted, fontSize: 13 }}>
        Two new files will be added to your HomePilot install. Nothing existing
        is modified.
      </p>

      <Section title={artefacts.dependenciesFilename} body={artefacts.dependenciesJson} />
      <Section title={artefacts.personaFilename} body={artefacts.personaContents} />

      <div style={{ ...helper, marginTop: 12 }}>
        Manifest hash: <code>{artefacts.manifestHash}</code>
      </div>

      <div style={{ marginTop: 16, display: 'flex', gap: 8, justifyContent: 'space-between' }}>
        <button type="button" style={buttonGhost} onClick={onBack}>
          Back
        </button>
        <button
          type="button"
          style={buttonPrimary}
          onClick={() => onSave(artefacts, config)}
        >
          Save &amp; enable
        </button>
      </div>
    </div>
  );
}

function Section({ title, body }: { title: string; body: string }) {
  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ color: palette.muted, fontSize: 12, marginBottom: 4 }}>
        <code>{title}</code>
      </div>
      <pre
        style={{
          background: palette.bg,
          color: palette.text,
          padding: 10,
          borderRadius: 6,
          fontSize: 12,
          maxHeight: 220,
          overflow: 'auto',
          margin: 0
        }}
      >
        {body}
      </pre>
    </div>
  );
}
