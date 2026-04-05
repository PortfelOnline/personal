import { router, protectedProcedure } from '../_core/trpc';
import { z } from 'zod';
import { execFileSync } from 'child_process';
import * as botManager from '../bots';
import * as orch from '../orchestrator';

const BOT_SERVER = 'root@167.86.116.15';
const SSH_KEY = `${process.env.HOME}/.ssh/id_ed25519`;
const SEARCH_RESULTS_PATH = '/root/yandex_bot/outputs/search_results.txt';

function fetchSearchResults(): string {
  try {
    return execFileSync('ssh', [
      '-i', SSH_KEY,
      '-o', 'StrictHostKeyChecking=no',
      '-o', 'ConnectTimeout=8',
      BOT_SERVER,
      `cat ${SEARCH_RESULTS_PATH}`,
    ], { timeout: 15_000, encoding: 'utf-8' });
  } catch {
    return '';
  }
}

function parseSearchStats(raw: string) {
  const byDate: Record<string, { serp: number; direct: number; total: number }> = {};
  for (const line of raw.split('\n')) {
    const parts = line.split('\t');
    if (parts.length < 4 || parts[0].startsWith('Bot ID')) continue;
    const date = parts[3]?.slice(0, 10);
    if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) continue;
    const type = parts[4]?.trim() || 'direct';
    if (!byDate[date]) byDate[date] = { serp: 0, direct: 0, total: 0 };
    if (type === 'serp') byDate[date].serp++;
    else byDate[date].direct++;
    byDate[date].total++;
  }
  return Object.entries(byDate)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, counts]) => ({ date, ...counts }));
}

const botEntrySchema = z.object({
  botId: z.number().int().min(1).max(100),
  website: z.string().url(),
  enabled: z.boolean(),
});

const orchestratorConfigSchema = z.object({
  enabled: z.boolean(),
  maxConcurrent: z.number().int().min(1).max(20),
  restartDelayMin: z.number().int().min(1).max(1440),
  dailyStartHour: z.number().int().min(0).max(23),
  dailyEndHour: z.number().int().min(1).max(24),
  bots: z.array(botEntrySchema),
});

const googleDocsSchema = z.object({
  global: z.object({
    proxies: z.string().url(),
    queries: z.string().url(),
    warmup_queries: z.string().url(),
  }),
  websites: z.record(z.string(), z.string()),
});

export const botsRouter = router({
  list: protectedProcedure.query(() => {
    const running = botManager.getRunningBots();
    const runningIds = new Set(running.map(b => b.botId));
    const knownIds = botManager.listKnownBotIds();

    const stopped = knownIds
      .filter(id => !runningIds.has(id))
      .map(id => ({ botId: id, status: 'stopped' as const, state: botManager.getBotState(id) }));

    const runningWithState = running.map(b => ({
      ...b,
      status: 'running' as const,
      state: botManager.getBotState(b.botId),
    }));

    return {
      bots: [...runningWithState, ...stopped].sort((a, b) => a.botId - b.botId),
      proxyStats: botManager.getProxyStats(),
    };
  }),

  start: protectedProcedure
    .input(z.object({
      botId: z.number().int().min(1).max(100),
      mode: z.enum(['warmup', 'target']),
      website: z.string().url(),
    }))
    .mutation(({ input }) => botManager.startBot(input.botId, input.mode, input.website)),

  stop: protectedProcedure
    .input(z.object({ botId: z.number().int() }))
    .mutation(({ input }) => botManager.stopBot(input.botId)),

  logs: protectedProcedure
    .input(z.object({ botId: z.number().int(), lines: z.number().int().default(150) }))
    .query(({ input }) => ({ logs: botManager.getBotLogs(input.botId, input.lines) })),

  clearCache: protectedProcedure.mutation(() => { botManager.clearProxyCache(); return { success: true }; }),
  clearBlacklist: protectedProcedure.mutation(() => { botManager.clearProxyBlacklist(); return { success: true }; }),

  // --- proxies.txt ---
  proxyList: protectedProcedure.query(() => {
    const { proxies } = botManager.getProxies();
    const blacklist = botManager.getProxyBlacklist();
    const now = new Date();
    return proxies.map(p => ({
      proxy: p,
      banned: p in blacklist && new Date(blacklist[p]) > now,
      banUntil: blacklist[p] ?? null,
    }));
  }),

  proxyAdd: protectedProcedure
    .input(z.object({ text: z.string() }))
    .mutation(({ input }) => {
      const lines = input.text.split('\n').map(l => l.trim()).filter(Boolean);
      return botManager.addProxies(lines);
    }),

  proxyReplace: protectedProcedure
    .input(z.object({ text: z.string() }))
    .mutation(({ input }) => {
      const lines = input.text.split('\n').map(l => l.trim()).filter(Boolean);
      return botManager.replaceProxies(lines);
    }),

  proxyDelete: protectedProcedure
    .input(z.object({ proxy: z.string() }))
    .mutation(({ input }) => botManager.deleteProxy(input.proxy)),

  // --- Google Docs config ---
  googleDocs: protectedProcedure.query(() => botManager.getGoogleDocs()),

  setGoogleDocs: protectedProcedure
    .input(googleDocsSchema)
    .mutation(({ input }) => { botManager.setGoogleDocs(input); return { success: true }; }),

  // --- Orchestrator ---
  orchestratorConfig: protectedProcedure.query(() => orch.getOrchestratorConfig()),

  orchestratorStatus: protectedProcedure.query(() => orch.getOrchestratorStatus()),

  setOrchestratorConfig: protectedProcedure
    .input(orchestratorConfigSchema)
    .mutation(({ input }) => { orch.saveOrchestratorConfig(input); return { success: true }; }),

  // --- Search CTR stats (reads from bot server via SSH) ---
  searchStats: protectedProcedure.query(() => {
    const raw = fetchSearchResults();
    return { rows: parseSearchStats(raw) };
  }),
});
