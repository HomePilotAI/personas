// packages/gitpilot-connect/src/wizard/Step6Persona.tsx
import React from 'react';
import { WizardState } from '../state.js';
import { buttonGhost, buttonPrimary, card, helper, input, label, palette } from './styles.js';

export interface Step6Props {
  state: WizardState;
  onChange: (next: Partial<WizardState>) => void;
  onBack: () => void;
  onContinue: () => void;
  /** Optional list of existing Coder persona slugs in the user's HomePilot install. */
  existingPersonas?: { slug: string; name: string }[];
}

export function Step6Persona({
  state,
  onChange,
  onBack,
  onContinue,
  existingPersonas
}: Step6Props): React.ReactElement {
  const slug = state.personaSlug;

  return (
    <div style={card}>
      <h3 style={{ margin: 0, color: palette.text }}>Bind to a persona</h3>
      <p style={{ color: palette.muted, fontSize: 13 }}>
        Either attach this connection to an existing Coder persona, or let the
        wizard generate a new one with sensible defaults.
      </p>

      <div style={{ marginTop: 12 }}>
        <label htmlFor="gp-persona-slug" style={label}>
          Persona slug
        </label>
        <input
          id="gp-persona-slug"
          type="text"
          value={slug}
          onChange={(e) =>
            onChange({ personaSlug: e.target.value.toLowerCase().replace(/[^a-z0-9-]+/g, '-') })
          }
          placeholder="coder-my-gitpilot"
          style={input}
        />
        <div style={helper}>
          Lowercase, dashes only. Used as the filename: <code>{slug || 'coder-?'}.hpersona</code>.
        </div>
      </div>

      {existingPersonas && existingPersonas.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <span style={label}>Or pick an existing one</span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {existingPersonas.map((p) => (
              <button
                key={p.slug}
                type="button"
                onClick={() => onChange({ personaSlug: p.slug })}
                style={{
                  ...buttonGhost,
                  borderColor: slug === p.slug ? palette.accent : palette.border,
                  color: slug === p.slug ? palette.accentText : palette.muted,
                  fontSize: 12
                }}
              >
                {p.name}
              </button>
            ))}
          </div>
        </div>
      )}

      <div style={{ marginTop: 16, display: 'flex', gap: 8, justifyContent: 'space-between' }}>
        <button type="button" style={buttonGhost} onClick={onBack}>
          Back
        </button>
        <button
          type="button"
          style={buttonPrimary}
          onClick={onContinue}
          aria-disabled={!slug || slug.length < 3}
        >
          Continue
        </button>
      </div>
    </div>
  );
}
