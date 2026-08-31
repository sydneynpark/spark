import { useMemo, useState } from 'react';

export function compareValues(a, b, key) {
  const aVal = a[key];
  const bVal = b[key];
  if (aVal == null && bVal == null) return 0;
  if (aVal == null) return -1;
  if (bVal == null) return 1;
  if (typeof aVal === 'string') return aVal.localeCompare(bVal, undefined, { sensitivity: 'base' });
  return aVal - bVal;
}

// Sorts `items` by a field selected from a SortBar. `defaultKey`/
// `defaultDirection` seed the initial sort; each SortBar option's own
// `defaultDirection` (e.g. ratings start high-to-low, titles start A-Z)
// takes over once the user switches to that field.
export function useSort(items, defaultKey, defaultDirection = 'asc') {
  const [sortKey, setSortKey] = useState(defaultKey);
  const [sortDirection, setSortDirection] = useState(defaultDirection);

  const sortedItems = useMemo(() => {
    const sorted = [...items].sort((a, b) => compareValues(a, b, sortKey));
    if (sortDirection === 'desc') sorted.reverse();
    return sorted;
  }, [items, sortKey, sortDirection]);

  const handleSort = (option) => {
    if (sortKey === option.key) {
      setSortDirection(dir => (dir === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(option.key);
      setSortDirection(option.defaultDirection || 'asc');
    }
  };

  return { sortedItems, sortKey, sortDirection, handleSort };
}
