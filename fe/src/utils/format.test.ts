import { describe, expect, it } from 'vitest';

import { formatBytes, formatDuration } from './format';

describe('formatBytes', () => {
  it('scales to the largest fitting unit', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(1023)).toBe('1023 B');
    expect(formatBytes(1536)).toBe('1.5 KB');
    expect(formatBytes(5 * 1024 * 1024)).toBe('5.0 MB');
  });
});

describe('formatDuration', () => {
  it('keeps the largest non-zero unit and the next one', () => {
    expect(formatDuration(0)).toBe('0s');
    expect(formatDuration(12)).toBe('12s');
    expect(formatDuration(312)).toBe('5m 12s');
    expect(formatDuration(3 * 86_400 + 4 * 3_600 + 5 * 60)).toBe('3d 4h');
    expect(formatDuration(4 * 3_600 + 5)).toBe('4h 0m');
    expect(formatDuration(-5)).toBe('0s');
  });
});
