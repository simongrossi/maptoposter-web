import { describe, expect, it } from 'vitest';
import { insertAtPosition, normalizeRequestedPosition, type RankingItem } from './ranking';

const a: RankingItem = { id: 'a', name: 'A', category: 'C1', origin: 'O1' };
const b: RankingItem = { id: 'b', name: 'B', category: 'C1', origin: 'O2' };
const c: RankingItem = { id: 'c', name: 'C', category: 'C2', origin: 'O1' };

describe('normalizeRequestedPosition', () => {
  it('normalizes invalid values', () => {
    expect(normalizeRequestedPosition(undefined)).toBeUndefined();
    expect(normalizeRequestedPosition(null)).toBeUndefined();
    expect(normalizeRequestedPosition(Number.NaN)).toBeUndefined();
    expect(normalizeRequestedPosition(0)).toBe(1);
    expect(normalizeRequestedPosition(-12)).toBe(1);
    expect(normalizeRequestedPosition(2.8)).toBe(2);
  });
});

describe('insertAtPosition', () => {
  it('adds item at requested 1-based position', () => {
    expect(insertAtPosition([a, b], c, 2).map((item) => item.id)).toEqual(['a', 'c', 'b']);
  });

  it('moves existing item instead of duplicating', () => {
    expect(insertAtPosition([a, b, c], b, 1).map((item) => item.id)).toEqual(['b', 'a', 'c']);
  });

  it('appends when no position is provided', () => {
    expect(insertAtPosition([a], b).map((item) => item.id)).toEqual(['a', 'b']);
  });
});
