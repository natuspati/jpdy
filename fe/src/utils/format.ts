const BYTE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB'] as const;

export function formatBytes(bytes: number): string {
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < BYTE_UNITS.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${unit === 0 ? value : value.toFixed(1)} ${BYTE_UNITS[unit]}`;
}

/** `3d 4h`, `4h 0m`, `5m 12s` or `12s`: the largest non-zero unit and the one after it. */
export function formatDuration(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const parts: Array<[number, string]> = [
    [Math.floor(seconds / 86_400), 'd'],
    [Math.floor((seconds % 86_400) / 3_600), 'h'],
    [Math.floor((seconds % 3_600) / 60), 'm'],
    [seconds % 60, 's'],
  ];
  const first = parts.findIndex(([value]) => value > 0);
  if (first === -1) return '0s';
  return parts
    .slice(first, first + 2)
    .map(([value, unit]) => `${value}${unit}`)
    .join(' ');
}
