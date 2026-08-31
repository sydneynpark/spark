import React from 'react';

// options: [{ key, label, defaultDirection }]
function SortBar({ options, sortKey, sortDirection, onSort }) {
  return (
    <div className="sort-bar">
      <span className="sort-bar-label">Sort by:</span>
      {options.map(option => {
        const active = sortKey === option.key;
        return (
          <button
            key={option.key}
            type="button"
            className={`sort-bar-button${active ? ' sort-bar-button--active' : ''}`}
            onClick={() => onSort(option)}
            aria-pressed={active}
          >
            {option.label}
            {active && (
              <span className="sort-bar-arrow" aria-hidden="true">
                {sortDirection === 'asc' ? '↑' : '↓'}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export default SortBar;
