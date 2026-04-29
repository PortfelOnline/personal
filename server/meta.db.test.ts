import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockDb = {
  select: vi.fn(),
  insert: vi.fn(),
  update: vi.fn(),
};

vi.mock('drizzle-orm/mysql2', () => ({
  drizzle: vi.fn(() => mockDb),
}));

vi.mock('drizzle-orm', () => ({
  eq: vi.fn((a: any, b: any) => ({ type: 'eq', column: a, value: b })),
  and: vi.fn((...args: any[]) => ({ type: 'and', conditions: args })),
}));

vi.mock('./_core/env', () => ({ ENV: {} }));

vi.mock('../drizzle/schema', () => ({
  metaAccounts: { name: 'meta_accounts' },
  InsertMetaAccount: Object,
  MetaAccount: Object,
}));

function makeSelectChain(result: any[]) {
  const chain: any = {
    from: vi.fn(() => chain),
    where: vi.fn(() => chain),
    limit: vi.fn(() => Promise.resolve(result)),
    then: (onfulfilled: any, onrejected: any) => Promise.resolve(result).then(onfulfilled, onrejected),
  };
  return chain;
}function mockSelect(result: any[]) {
  const chain = makeSelectChain(result);
  mockDb.select.mockReturnValue(chain);
  return chain;
}

function mockInsert() {
  const chain = {
    values: vi.fn(() => Promise.resolve({ insertId: 1 })),
  };
  mockDb.insert.mockReturnValue(chain);
  return chain;
}

function mockUpdate() {
  const chain: any = {
    set: vi.fn(() => chain),
    where: vi.fn(() => Promise.resolve({ affectedRows: 1 })),
  };
  mockDb.update.mockReturnValue(chain);
  return chain;
}

describe('meta.db', () => {
  beforeEach(() => {
    vi.resetModules();
    process.env.DATABASE_URL = 'mysql://test:test@localhost:3306/test';
    mockDb.select.mockReset();
    mockDb.insert.mockReset();
    mockDb.update.mockReset();
  });

  describe('upsertMetaAccount', () => {
    it('updates existing account when found', async () => {
      const existing = { id: 1, userId: 1, accountId: 'act_123', isActive: 1 };
      const mockSelectChain = mockSelect([existing]);
      mockUpdate();

      const { upsertMetaAccount } = await import('./meta.db');
      const result = await upsertMetaAccount(1, {
        accountId: 'act_123',
        accessToken: 'new_token',
      } as any);

      // Should find existing
      expect(mockSelectChain.limit).toHaveBeenCalledWith(1);
      // Should update (not insert)
      expect(mockDb.update).toHaveBeenCalled();
      expect(mockDb.insert).not.toHaveBeenCalled();
      expect(result).toEqual(existing);
    });

    it('inserts new account when not found', async () => {
      mockDb.select.mockReturnValueOnce(makeSelectChain([]));
      mockInsert();
      mockDb.select.mockReturnValue(makeSelectChain([{ id: 2, userId: 1, accountId: 'act_456', accessToken: 'tok' }]));

      const { upsertMetaAccount } = await import('./meta.db');
      const result = await upsertMetaAccount(1, {
        accountId: 'act_456',
        accessToken: 'tok',
      } as any);

      expect(mockDb.insert).toHaveBeenCalled();
      expect(result).toEqual({ id: 2, userId: 1, accountId: 'act_456', accessToken: 'tok' });
    });

    it('throws when database is not available', async () => {
      delete process.env.DATABASE_URL;
      const { upsertMetaAccount } = await import('./meta.db');
      await expect(upsertMetaAccount(1, { accountId: 'act' } as any)).rejects.toThrow('Database not available');
    });
  });

  describe('getUserMetaAccounts', () => {
    it('returns active accounts for user', async () => {
      const accounts = [
        { id: 1, userId: 1, accountId: 'act_1', isActive: 1 },
        { id: 2, userId: 1, accountId: 'act_2', isActive: 1 },
      ];
      mockSelect(accounts);

      const { getUserMetaAccounts } = await import('./meta.db');
      const result = await getUserMetaAccounts(1);

      expect(result).toEqual(accounts);
      expect(mockDb.select).toHaveBeenCalled();
    });

    it('returns [] on error', async () => {
      mockSelect([]);
      mockDb.select.mockReturnValue({
        from: vi.fn(() => ({
          where: vi.fn(() => { throw new Error('DB error'); }),
        })),
      });

      const { getUserMetaAccounts } = await import('./meta.db');
      const result = await getUserMetaAccounts(1);

      expect(result).toEqual([]);
    });
  });

  describe('getMetaAccount', () => {
    it('returns account when found', async () => {
      mockSelect([{ id: 1, userId: 1, accountId: 'act_789' }]);

      const { getMetaAccount } = await import('./meta.db');
      const result = await getMetaAccount(1, 'act_789');

      expect(result).toEqual({ id: 1, userId: 1, accountId: 'act_789' });
    });

    it('returns null when not found', async () => {
      mockSelect([]);

      const { getMetaAccount } = await import('./meta.db');
      const result = await getMetaAccount(1, 'act_missing');

      expect(result).toBeNull();
    });

    it('returns null on error', async () => {
      mockDb.select.mockReturnValue({
        from: vi.fn(() => ({
          where: vi.fn(() => ({
            limit: vi.fn(() => { throw new Error('DB error'); }),
          })),
        })),
      });

      const { getMetaAccount } = await import('./meta.db');
      const result = await getMetaAccount(1, 'act_err');

      expect(result).toBeNull();
    });
  });

  describe('deactivateMetaAccount', () => {
    it('sets isActive to 0 and returns true', async () => {
      mockUpdate();

      const { deactivateMetaAccount } = await import('./meta.db');
      const result = await deactivateMetaAccount(1, 'act_123');

      expect(result).toBe(true);
      expect(mockDb.update).toHaveBeenCalled();
    });

    it('returns false on error', async () => {
      mockDb.update.mockReturnValue({
        set: vi.fn(() => ({
          where: vi.fn(() => { throw new Error('DB error'); }),
        })),
      });

      const { deactivateMetaAccount } = await import('./meta.db');
      const result = await deactivateMetaAccount(1, 'act_err');

      expect(result).toBe(false);
    });
  });

  describe('updateMetaAccountToken', () => {
    it('updates token and returns true', async () => {
      mockUpdate();

      const { updateMetaAccountToken } = await import('./meta.db');
      const result = await updateMetaAccountToken(1, 'act_123', 'new_token', new Date('2027-01-01'));

      expect(result).toBe(true);
      expect(mockDb.update).toHaveBeenCalled();
    });

    it('updates token without expiresAt', async () => {
      mockUpdate();

      const { updateMetaAccountToken } = await import('./meta.db');
      const result = await updateMetaAccountToken(1, 'act_123', 'new_token');

      expect(result).toBe(true);
    });

    it('returns false on error', async () => {
      mockDb.update.mockReturnValue({
        set: vi.fn(() => ({
          where: vi.fn(() => { throw new Error('DB error'); }),
        })),
      });

      const { updateMetaAccountToken } = await import('./meta.db');
      const result = await updateMetaAccountToken(1, 'act_err', 'tok');

      expect(result).toBe(false);
    });
  });
});
