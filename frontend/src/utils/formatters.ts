/**
 * Standard enterprise data formatters for the WIMLOGIC client.
 */

/**
 * Formats a numeric value as US currency (USD).
 * @param value The number or string representing the dollar amount.
 * @param minimumFractionDigits The minimum number of decimal places (default is 0 for compact real estate values).
 */
export function formatCurrency(value: number | string | undefined | null, minimumFractionDigits: number = 0): string {
  if (value === undefined || value === null) return '—';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '—';

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits,
    maximumFractionDigits: 2,
  }).format(num);
}

/**
 * Formats a area value in Square Feet (SF) or Acres (AC).
 * @param value Square footage or acreage value.
 * @param unit The unit to display ('SF' | 'AC' | 'sqft' | 'acres')
 */
export function formatArea(value: number | string | undefined | null, unit: 'SF' | 'AC' | 'sqft' | 'acres' = 'SF'): string {
  if (value === undefined || value === null) return '—';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '—';

  const formattedNum = new Intl.NumberFormat('en-US', {
    maximumFractionDigits: unit === 'AC' || unit === 'acres' ? 2 : 0,
  }).format(num);

  const displayUnit = unit === 'SF' || unit === 'sqft' ? 'SF' : 'Acres';
  return `${formattedNum} ${displayUnit}`;
}

/**
 * Formats a date string or timestamp into a standard human-readable format.
 * @param dateVal Date string, Date object, or timestamp.
 * @param includeTime Whether to include hours and minutes.
 */
export function formatDate(dateVal: string | Date | number | undefined | null, includeTime: boolean = false): string {
  if (!dateVal) return '—';
  try {
    const date = typeof dateVal === 'string' || typeof dateVal === 'number' ? new Date(dateVal) : dateVal;
    if (isNaN(date.getTime())) return '—';

    const options: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    };

    if (includeTime) {
      options.hour = '2-digit';
      options.minute = '2-digit';
    }

    return new Intl.DateTimeFormat('en-US', options).format(date);
  } catch {
    return '—';
  }
}

/**
 * Formats a raw number as a standard localized integer or float.
 */
export function formatNumber(value: number | string | undefined | null, maxDecimals: number = 2): string {
  if (value === undefined || value === null) return '—';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '—';

  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: maxDecimals,
  }).format(num);
}

/**
 * Capitalizes the first letter of each word in a string.
 */
export function capitalizeWords(str: string | undefined | null): string {
  if (!str) return '';
  return str
    .toLowerCase()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Truncates a string to a specified length and appends ellipses.
 */
export function truncateString(str: string | undefined | null, length: number = 50): string {
  if (!str) return '';
  if (str.length <= length) return str;
  return `${str.substring(0, length)}...`;
}

/**
 * Formats a phone number to standard (XXX) XXX-XXXX format.
 */
export function formatPhoneNumber(phone: string | undefined | null): string {
  if (!phone) return '—';
  const cleaned = phone.replace(/\D/g, '');
  const match = cleaned.match(/^(\d{3})(\d{3})(\d{4})$/);
  if (match) {
    return `(${match[1]}) ${match[2]}-${match[3]}`;
  }
  return phone;
}
