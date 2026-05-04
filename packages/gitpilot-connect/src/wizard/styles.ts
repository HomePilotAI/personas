// packages/gitpilot-connect/src/wizard/styles.ts
//
// Inline-style tokens used by the wizard components. We avoid pulling
// in a CSS-in-JS lib so the package stays additive: zero global style
// pollution, no PostCSS step required by the consumer.

export const palette = {
  bg: '#0f1018',
  surface: '#1a1b26',
  surface2: '#252634',
  border: '#2a2b36',
  text: '#e0e0e7',
  muted: '#a0a0b0',
  faint: '#7a7d8a',
  accent: '#3B82F6',
  accentSoft: '#1e3a5f',
  accentText: '#93c5fd',
  ok: '#10b981',
  okBg: '#0f3a26',
  okText: '#86efac',
  warn: '#f59e0b',
  warnBg: '#3a2e0f',
  warnText: '#fcd34d',
  bad: '#ef4444',
  badBg: '#3a0f0f',
  badText: '#fca5a5'
};

export const card: React.CSSProperties = {
  background: palette.surface,
  border: `1px solid ${palette.border}`,
  borderRadius: 8,
  padding: 20
};

export const label: React.CSSProperties = {
  display: 'block',
  fontSize: 12,
  color: palette.muted,
  marginBottom: 4
};

export const input: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  background: palette.bg,
  color: palette.text,
  border: `1px solid ${palette.border}`,
  borderRadius: 6,
  fontSize: 13,
  boxSizing: 'border-box'
};

export const buttonPrimary: React.CSSProperties = {
  padding: '8px 16px',
  background: palette.accent,
  color: '#fff',
  border: 'none',
  borderRadius: 6,
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 600
};

export const buttonGhost: React.CSSProperties = {
  padding: '8px 16px',
  background: 'transparent',
  color: palette.muted,
  border: `1px solid ${palette.border}`,
  borderRadius: 6,
  cursor: 'pointer',
  fontSize: 13
};

export const helper: React.CSSProperties = {
  fontSize: 11,
  color: palette.faint,
  marginTop: 4
};

export const badge = (kind: 'ok' | 'warn' | 'bad' | 'info'): React.CSSProperties => {
  const map = {
    ok: { bg: palette.okBg, text: palette.okText },
    warn: { bg: palette.warnBg, text: palette.warnText },
    bad: { bg: palette.badBg, text: palette.badText },
    info: { bg: palette.accentSoft, text: palette.accentText }
  };
  const c = map[kind];
  return {
    display: 'inline-block',
    padding: '2px 8px',
    background: c.bg,
    color: c.text,
    borderRadius: 10,
    fontSize: 11,
    fontWeight: 600
  };
};
