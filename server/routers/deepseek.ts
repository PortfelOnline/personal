import { router, protectedProcedure } from '../_core/trpc';
import { z } from 'zod';
import https from 'https';

const AGENT_HOST = '167.86.116.15';
const AGENT_PORT = 8766;

function agentFetch(path: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const req = https.get({ hostname: AGENT_HOST, port: AGENT_PORT, path, timeout: 10_000 }, (res) => {
      let data = '';
      res.on('data', (chunk) => (data += chunk));
      res.on('end', () => resolve(data));
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('timeout')); });
  });
}

export const deepseekRouter = router({
  health: protectedProcedure.query(async () => {
    try {
      const raw = await agentFetch('/health');
      return JSON.parse(raw) as Record<string, unknown>;
    } catch {
      return { status: 'unreachable', error: 'Agent not reachable' };
    }
  }),

  tools: protectedProcedure.query(async () => {
    try {
      const raw = await agentFetch('/tools');
      return JSON.parse(raw) as string[];
    } catch {
      return [];
    }
  }),

  tasks: protectedProcedure.query(async () => {
    try {
      const raw = await agentFetch('/tasks');
      return JSON.parse(raw) as Record<string, unknown>;
    } catch {
      return { error: 'Cannot fetch tasks' };
    }
  }),

  createApiKey: protectedProcedure
    .input(z.object({ name: z.string().min(1).max(100) }))
    .mutation(async ({ input }) => {
      const body = JSON.stringify({ name: input.name, action: 'create-api-key' });
      const res = await fetch(`https://${AGENT_HOST}:${AGENT_PORT}/api/run/create-api-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json() as Promise<{ key: string; name: string; created_at: string }>;
    }),

  revokeApiKey: protectedProcedure
    .input(z.object({ key: z.string().min(1) }))
    .mutation(async ({ input }) => {
      const body = JSON.stringify({ key: input.key, action: 'revoke-api-key' });
      const res = await fetch(`https://${AGENT_HOST}:${AGENT_PORT}/api/run/revoke-api-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json() as Promise<{ revoked: string; name: string }>;
    }),

  listApiKeys: protectedProcedure.query(async () => {
    try {
      const raw = await agentFetch('/api/run/list-api-keys');
      return JSON.parse(raw) as Array<{ prefix: string; name: string; created_at: string; last_used_at: string; role: string }>;
    } catch {
      return [];
    }
  }),
});
