// packages/gitpilot-connect/src/wizard/Step4Workspace.tsx
import React, { useEffect, useState } from 'react';
import { GitPilotClient } from '../client.js';
import { WizardState } from '../state.js';
import { WorkspaceTarget } from '../types.js';
import { buttonGhost, buttonPrimary, card, helper, input, label, palette } from './styles.js';

export interface Step4Props {
  state: WizardState;
  onChange: (next: Partial<WizardState>) => void;
  onBack: () => void;
  onContinue: () => void;
  fetchImpl?: typeof fetch;
}

type Mode = 'github' | 'local';

interface RepoSummary {
  owner: string;
  name: string;
  default_branch: string;
  private: boolean;
  updated_at?: string;
}

export function Step4Workspace({
  state,
  onChange,
  onBack,
  onContinue,
  fetchImpl
}: Step4Props): React.ReactElement {
  const [mode, setMode] = useState<Mode>(state.workspace?.kind ?? 'github');
  const [repos, setRepos] = useState<RepoSummary[]>([]);
  const [branches, setBranches] = useState<string[]>([]);
  const [filter, setFilter] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== 'github' || !state.tokenInMemory) return;
    let cancelled = false;
    setBusy(true);
    setError(null);
    void new GitPilotClient({
      endpoint: state.endpoint,
      token: state.tokenInMemory,
      fetchImpl
    })
      .callTool('gitpilot.list_repos', { per_page: 50 })
      .then((env) => {
        if (cancelled) return;
        const result = env.result as { available?: boolean; repos?: RepoSummary[] } | undefined;
        setRepos(result?.repos ?? []);
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
      .finally(() => !cancelled && setBusy(false));
    return () => {
      cancelled = true;
    };
  }, [mode, state.endpoint, state.tokenInMemory, fetchImpl]);

  const pickGithub = async (repo: RepoSummary) => {
    onChange({
      workspace: {
        kind: 'github',
        owner: repo.owner,
        repo: repo.name,
        branch: repo.default_branch
      }
    });
    if (!state.tokenInMemory) return;
    try {
      const env = await new GitPilotClient({
        endpoint: state.endpoint,
        token: state.tokenInMemory,
        fetchImpl
      }).callTool('gitpilot.list_branches', { owner: repo.owner, repo: repo.name });
      const result = env.result as { branches?: { name: string }[] } | undefined;
      setBranches((result?.branches ?? []).map((b) => b.name));
    } catch {
      setBranches([repo.default_branch]);
    }
  };

  const ws = state.workspace;
  const filtered = repos.filter(
    (r) => !filter || `${r.owner}/${r.name}`.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div style={card}>
      <h3 style={{ margin: 0, color: palette.text }}>Pick your workspace</h3>
      <p style={{ color: palette.muted, fontSize: 13 }}>
        The Coder persona will be scoped to this repo or folder.
      </p>

      <div role="radiogroup" aria-label="Workspace mode" style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        {(['github', 'local'] as Mode[]).map((m) => (
          <button
            key={m}
            type="button"
            role="radio"
            aria-checked={mode === m}
            style={{
              ...buttonGhost,
              borderColor: mode === m ? palette.accent : palette.border,
              color: mode === m ? palette.accentText : palette.muted
            }}
            onClick={() => setMode(m)}
          >
            {m === 'github' ? 'GitHub repository' : 'Local folder'}
          </button>
        ))}
      </div>

      {mode === 'github' && (
        <div style={{ marginTop: 12 }}>
          <label htmlFor="gp-repo-filter" style={label}>
            Filter
          </label>
          <input
            id="gp-repo-filter"
            type="search"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="owner/name"
            style={input}
          />
          {busy && <div style={helper}>Loading repos…</div>}
          {error && <div style={{ ...helper, color: palette.badText }}>{error}</div>}
          <ul role="listbox" style={{ listStyle: 'none', margin: '8px 0', padding: 0, maxHeight: 220, overflow: 'auto' }}>
            {filtered.map((r) => {
              const selected =
                ws?.kind === 'github' && ws.owner === r.owner && ws.repo === r.name;
              return (
                <li key={`${r.owner}/${r.name}`}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={selected}
                    onClick={() => pickGithub(r)}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: '6px 10px',
                      background: selected ? palette.accentSoft : 'transparent',
                      color: selected ? palette.accentText : palette.text,
                      border: `1px solid ${selected ? palette.accent : palette.border}`,
                      borderRadius: 6,
                      marginBottom: 4,
                      cursor: 'pointer',
                      fontSize: 13
                    }}
                  >
                    {r.owner}/{r.name}
                    <span style={{ marginLeft: 8, color: palette.faint, fontSize: 11 }}>
                      {r.default_branch}
                      {r.private ? ' · private' : ''}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          {ws?.kind === 'github' && (
            <div>
              <label htmlFor="gp-branch" style={label}>
                Branch
              </label>
              <select
                id="gp-branch"
                value={ws.branch}
                onChange={(e) =>
                  onChange({
                    workspace: { ...ws, branch: e.target.value } as WorkspaceTarget
                  })
                }
                style={input}
              >
                {(branches.length ? branches : [ws.branch]).map((b) => (
                  <option key={b} value={b}>
                    {b}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {mode === 'local' && (
        <div style={{ marginTop: 12 }}>
          <label htmlFor="gp-localpath" style={label}>
            Folder path
          </label>
          <input
            id="gp-localpath"
            type="text"
            value={ws?.kind === 'local' ? ws.path : ''}
            onChange={(e) =>
              onChange({
                workspace: { kind: 'local', path: e.target.value }
              })
            }
            placeholder="/path/to/your/project"
            style={input}
          />
          <div style={helper}>Absolute path on the host where GitPilot runs.</div>
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
          aria-disabled={!ws}
        >
          Continue
        </button>
      </div>
    </div>
  );
}
