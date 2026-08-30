const dateTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
});

export function formatLocalDateTime(value: string): string {
  const parts = dateTimeFormatter.formatToParts(new Date(value));
  const getPart = (type: Intl.DateTimeFormatPartTypes): string =>
    parts.find((part) => part.type === type)?.value ?? '';

  return `${getPart('day')} ${getPart('month')}, ${getPart('year')} ${getPart('hour')}:${getPart('minute')}`;
}
