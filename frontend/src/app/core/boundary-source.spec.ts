import { describe, expect, it } from 'vitest';
import { BOUNDARY_SOURCE_KEY, DEFAULT_TILES_URL, dayNumber, readBoundarySource, readTilesUrl } from './boundary-source';

function mem(init: Record<string, string> = {}) {
  const m = new Map(Object.entries(init));
  return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v), m };
}

describe('boundary source flag', () => {
  it('defaults to geojson', () => {
    expect(readBoundarySource('', mem())).toBe('geojson');
    expect(readBoundarySource('?boundarySource=bogus', mem())).toBe('geojson');
  });
  it('query param wins and is remembered; geojson switches back', () => {
    const s = mem();
    expect(readBoundarySource('?date=1940-07-15&boundarySource=tiles', s)).toBe('tiles');
    expect(s.m.get(BOUNDARY_SOURCE_KEY)).toBe('tiles');
    expect(readBoundarySource('', s)).toBe('tiles');
    expect(readBoundarySource('?boundarySource=geojson', s)).toBe('geojson');
    expect(readBoundarySource('', s)).toBe('geojson');
  });
  it('tiles url: param, then stored, then default Martin', () => {
    const s = mem();
    expect(readTilesUrl('', s)).toBe(DEFAULT_TILES_URL);
    expect(readTilesUrl('?tilesUrl=http://x/y', s)).toBe('http://x/y');
    expect(readTilesUrl('', s)).toBe('http://x/y');
  });
});

describe('dayNumber（與 boundary_periods 的整數日一致）', () => {
  it('counts days from 1900-01-01, negative before', () => {
    expect(dayNumber('1900-01-01')).toBe(0);
    expect(dayNumber('1899-12-25')).toBe(-7);
    expect(dayNumber('1920-06-04')).toBe(7459);
    expect(dayNumber('1940-07-15')).toBe(14805);
    expect(dayNumber('1278-01-01')).toBe(-227180); // 開發庫最早的 start_day
  });
});
