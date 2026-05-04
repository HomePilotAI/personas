// packages/gitpilot-connect/src/types.ts
//
// All persisted shapes are defined as zod schemas; we derive the static
// types from the schemas so validation and TypeScript stay in sync.

import { z } from 'zod';

export const PermissionScopes = ['read', 'plan', 'mutation'] as const;
export type PermissionScope = (typeof PermissionScopes)[number];

export const WorkspaceTargetSchema = z.discriminatedUnion('kind', [
  z.object({
    kind: z.literal('github'),
    owner: z.string().min(1),
    repo: z.string().min(1),
    branch: z.string().min(1)
  }),
  z.object({
    kind: z.literal('local'),
    path: z.string().min(1)
  })
]);
export type WorkspaceTarget = z.infer<typeof WorkspaceTargetSchema>;

export const ConnectionConfigSchema = z.object({
  // Stable name the persona references. Lowercase, dash-separated.
  name: z
    .string()
    .min(1)
    .max(64)
    .regex(/^[a-z0-9][a-z0-9-]*$/, 'lowercase letters, digits and dashes only'),

  // GitPilot MCP server endpoint, including mount path.
  endpoint: z.string().url(),

  // How the wizard refers to the auth token. Either inline (development)
  // or a keychain entry name (production). The actual secret never
  // touches the persona file.
  auth: z.discriminatedUnion('source', [
    z.object({ source: z.literal('inline'), token: z.string().min(8) }),
    z.object({ source: z.literal('keychain'), entryName: z.string().min(1) })
  ]),

  // Subset of the server's tool catalog the wizard ticked.
  enabledTools: z.array(z.string().min(1)).min(1),

  // Permission scopes the user agreed to.
  scopes: z.array(z.enum(PermissionScopes)).min(1),

  // Pinned workspace.
  workspace: WorkspaceTargetSchema,

  // ISO timestamp of last successful connection test.
  verifiedAt: z.string().datetime().optional(),

  // Hash of the manifest the wizard wrote, so we can detect drift on
  // re-open and ask before overwriting hand-edits.
  manifestHash: z.string().optional()
});
export type ConnectionConfig = z.infer<typeof ConnectionConfigSchema>;
