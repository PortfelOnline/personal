import { describe, it, expect } from 'vitest';
import { getScPosColor } from './scTableHelpers';

describe('getScPosColor', () => {
  it('returns green for pos <= 3', () => {
    expect(getScPosColor(1)).toContain('green');
    expect(getScPosColor(3)).toContain('green');
  });
});

import { getScPotentialColor } from './scTableHelpers';

describe('getScPotentialColor', () => {
  it('returns green for potential >= 2000', () => {
    expect(getScPotentialColor(2000)).toContain('green');
    expect(getScPotentialColor(5000)).toContain('green');
  });
});

import { isCtrLow } from './scTableHelpers';

describe('isCtrLow', () => {
  it('returns true when ctr < 2 and pos <= 10', () => {
    expect(isCtrLow(1.5, 5)).toBe(true);
    expect(isCtrLow(0, 1)).toBe(true);
  });
});
