// photo.date is a 'YYYY-MM-DD' string, read from the photo's EXIF capture
// date (see the UpdatePhotoMetadata Lambda) — not every photo has one.
const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const WEEKDAY_FORMATTER = new Intl.DateTimeFormat('en-US', { weekday: 'short' });

export const DATE_FILTER_TYPES = ['year', 'month', 'day'];

export function getPhotoDateParts(photo) {
  if (!photo.date) return null;
  const [year, month, day] = photo.date.split('-');
  return { year, month, day };
}

export function monthName(month) {
  return MONTH_NAMES[Number(month) - 1] || month;
}

export function monthValue({ year, month }) {
  return `${year}-${month}`;
}

export function dayValue({ year, month, day }) {
  return `${year}-${month}-${day}`;
}

export function formatDayLabel({ year, month, day }) {
  const date = new Date(Number(year), Number(month) - 1, Number(day));
  return `${parseInt(day, 10)} · ${WEEKDAY_FORMATTER.format(date)}`;
}

// Renders the /gallery filter chip label for a year/month/day value, e.g.
// year "2025" -> "2025", month "2025-05" -> "May 2025", day "2025-05-17" -> "May 17, 2025".
export function formatDateFilterLabel(type, value) {
  if (type === 'year') return value;
  const [year, month, day] = value.split('-');
  if (type === 'month') return `${monthName(month)} ${year}`;
  return `${monthName(month)} ${parseInt(day, 10)}, ${year}`;
}
