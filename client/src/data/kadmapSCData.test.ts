import { describe, it, expect } from 'vitest';
import { SC_DATA } from './kadmapSCData';

describe('SC_DATA', () => {
  it('has at least one row', () => {
    expect(SC_DATA.length).toBeGreaterThan(0);
  });

  it('each row has required ScRow fields with correct types', () => {
    const row = SC_DATA[0];
    expect(typeof row.slug).toBe('string');
    expect(typeof row.pos).toBe('number');
    expect(typeof row.impressions).toBe('number');
    expect(typeof row.clicks).toBe('number');
    expect(typeof row.ctr).toBe('number');
    expect(typeof row.potential).toBe('number');
  });

  it('is sorted by potential descending', () => {
    for (let i = 1; i < SC_DATA.length; i++) {
      expect(SC_DATA[i - 1].potential).toBeGreaterThanOrEqual(SC_DATA[i].potential);
    }
  });
});
