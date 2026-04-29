import { describe, expect, it, vi, beforeEach } from 'vitest';
import { EventEmitter } from 'events';

const mockHttpGet = vi.fn();
vi.mock('http', () => ({
  default: { get: mockHttpGet },
  get: mockHttpGet,
}));

function makeMockSuccess(body: string) {
  const res = new EventEmitter();
  const req = new EventEmitter() as any;
  req.destroy = vi.fn();
  mockHttpGet.mockImplementation((_opts: any, callback: (r: typeof res) => void) => {
    callback(res);
    process.nextTick(() => {
      res.emit('data', body);
      res.emit('end');
    });
    return req;
  });
}

function makeMockError(error: Error) {
  mockHttpGet.mockImplementation(() => {
    const req = new EventEmitter() as any;
    req.destroy = vi.fn();
    process.nextTick(() => req.emit('error', error));
    return req;
  });
}

const mockUser = { id: 1, name: 'test', email: 'test@test.com', role: 'admin' } as any;
const mockReq = { headers: {} } as any;
const mockRes = {} as any;
const ctx = { req: mockReq, res: mockRes, user: mockUser };

describe('deepseekRouter', () => {
  beforeEach(() => {
    mockHttpGet.mockReset();
  });

  describe('health', () => {
    it('returns health data on success', async () => {
      makeMockSuccess(JSON.stringify({ status: 'healthy', uptime: 12345 }));
      const { deepseekRouter } = await import('./deepseek');
      const caller = (deepseekRouter as any).createCaller(ctx);

      const result = await caller.health();
      expect(result).toEqual({ status: 'healthy', uptime: 12345 });
    });

    it('returns unreachable on error', async () => {
      makeMockError(new Error('ECONNREFUSED'));
      const { deepseekRouter } = await import('./deepseek');
      const caller = (deepseekRouter as any).createCaller(ctx);

      const result = await caller.health();
      expect(result).toEqual({ status: 'unreachable', error: 'Agent not reachable' });
    });
  });

  describe('services', () => {
    it('returns services data on success', async () => {
      makeMockSuccess(JSON.stringify({ services: ['deepseek'], count: 1 }));
      const { deepseekRouter } = await import('./deepseek');
      const caller = (deepseekRouter as any).createCaller(ctx);

      const result = await caller.services();
      expect(result).toEqual({ services: ['deepseek'], count: 1 });
    });

    it('returns null on error', async () => {
      makeMockError(new Error('timeout'));
      const { deepseekRouter } = await import('./deepseek');
      const caller = (deepseekRouter as any).createCaller(ctx);

      const result = await caller.services();
      expect(result).toBeNull();
    });
  });

  describe('tasks', () => {
    it('returns tasks data on success', async () => {
      makeMockSuccess(JSON.stringify({ tasks: [], queue: 0 }));
      const { deepseekRouter } = await import('./deepseek');
      const caller = (deepseekRouter as any).createCaller(ctx);

      const result = await caller.tasks();
      expect(result).toEqual({ tasks: [], queue: 0 });
    });

    it('returns error object on failure', async () => {
      makeMockError(new Error('ECONNREFUSED'));
      const { deepseekRouter } = await import('./deepseek');
      const caller = (deepseekRouter as any).createCaller(ctx);

      const result = await caller.tasks();
      expect(result).toEqual({ error: 'Cannot fetch tasks' });
    });
  });

  describe('sessions', () => {
    it('returns sessions data on success', async () => {
      makeMockSuccess(JSON.stringify({ sessions: ['sess_1'], active: 1 }));
      const { deepseekRouter } = await import('./deepseek');
      const caller = (deepseekRouter as any).createCaller(ctx);

      const result = await caller.sessions();
      expect(result).toEqual({ sessions: ['sess_1'], active: 1 });
    });

    it('returns [] on error', async () => {
      makeMockError(new Error('timeout'));
      const { deepseekRouter } = await import('./deepseek');
      const caller = (deepseekRouter as any).createCaller(ctx);

      const result = await caller.sessions();
      expect(result).toEqual([]);
    });
  });

  describe('permissions', () => {
    it('returns permissions data on success', async () => {
      makeMockSuccess(JSON.stringify({ admin: true, scopes: ['read', 'write'] }));
      const { deepseekRouter } = await import('./deepseek');
      const caller = (deepseekRouter as any).createCaller(ctx);

      const result = await caller.permissions();
      expect(result).toEqual({ admin: true, scopes: ['read', 'write'] });
    });

    it('returns null on error', async () => {
      makeMockError(new Error('ECONNREFUSED'));
      const { deepseekRouter } = await import('./deepseek');
      const caller = (deepseekRouter as any).createCaller(ctx);

      const result = await caller.permissions();
      expect(result).toBeNull();
    });
  });

  describe('bgTasks', () => {
    it('returns bgTasks data on success', async () => {
      makeMockSuccess(JSON.stringify({ tasks: ['bg_1'], running: 1 }));
      const { deepseekRouter } = await import('./deepseek');
      const caller = (deepseekRouter as any).createCaller(ctx);

      const result = await caller.bgTasks();
      expect(result).toEqual({ tasks: ['bg_1'], running: 1 });
    });

    it('returns [] on error', async () => {
      makeMockError(new Error('ECONNREFUSED'));
      const { deepseekRouter } = await import('./deepseek');
      const caller = (deepseekRouter as any).createCaller(ctx);

      const result = await caller.bgTasks();
      expect(result).toEqual([]);
    });
  });
});
