import { useState, useId } from 'react';

const MAX_SUGGESTIONS = 8;

function findTag(tags, tag) {
  return tags.find(t => t.toLowerCase() === tag.toLowerCase());
}

// Tags as removable chips, and a box to add more to, which suggests the
// tags already in use (`suggestions`, most used first) as you type, to
// reuse rather than respell. A tag typed in another case than one in use is
// added as the one in use. Enter or a comma adds a tag; Backspace in the
// empty box removes the last. Without `allowNew`, only suggested tags can be
// added, Enter adding the first suggestion for what's typed -- e.g. to pick
// tags to filter by.
function TagInput({
  tags, onChange, suggestions = [], allowNew = true, labelledBy,
  placeholder = tags.length ? 'Add another tag' : 'Add a tag',
}) {
  const listId = useId();
  const [text, setText] = useState('');
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(-1);

  const query = text.trim().toLowerCase();
  const matches = suggestions
    .filter(tag => !findTag(tags, tag) && tag.toLowerCase().includes(query))
    // Ones it starts with first, else most used first, as given.
    .sort((a, b) => Number(b.toLowerCase().startsWith(query)) - Number(a.toLowerCase().startsWith(query)))
    .slice(0, MAX_SUGGESTIONS);
  const showList = open && matches.length > 0;

  function addTags(newTags) {
    const next = [...tags];
    newTags.forEach(raw => {
      const typed = raw.split(/\s+/).filter(Boolean).join(' ');
      const suggested = findTag(suggestions, typed);
      if (!typed || findTag(next, typed) || (!allowNew && !suggested)) return;
      next.push(suggested || typed);
    });
    if (next.length !== tags.length) onChange(next);
    setText('');
    setHighlight(-1);
  }

  function handleChange(e) {
    // A comma ends a tag, including in pasted text.
    const parts = e.target.value.split(',');
    if (parts.length > 1) {
      addTags(parts.slice(0, -1));
      setText(parts[parts.length - 1]);
    } else {
      setText(e.target.value);
      setHighlight(-1);
    }
    setOpen(true);
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (showList && highlight >= 0) addTags([matches[highlight]]);
      else if (!allowNew && query && matches.length > 0) addTags([matches[0]]);
      else addTags([text]);
    } else if (e.key === 'ArrowDown' && matches.length > 0) {
      e.preventDefault();
      setOpen(true);
      setHighlight(h => (h + 1) % matches.length);
    } else if (e.key === 'ArrowUp' && matches.length > 0) {
      e.preventDefault();
      setOpen(true);
      setHighlight(h => (h <= 0 ? matches.length - 1 : h - 1));
    } else if (e.key === 'Escape') {
      setOpen(false);
      setHighlight(-1);
    } else if (e.key === 'Backspace' && text === '' && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  }

  return (
    <div className="tag-input">
      {tags.map(tag => (
        <span key={tag} className="tag-chip">
          {tag}
          <button
            type="button"
            className="tag-chip-remove"
            onClick={() => onChange(tags.filter(t => t !== tag))}
            aria-label={`Remove tag ${tag}`}
          >
            ×
          </button>
        </span>
      ))}
      <div className="tag-input-box">
        <input
          type="text"
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => setOpen(true)}
          onBlur={() => { addTags([text]); setOpen(false); }}
          placeholder={placeholder}
          aria-labelledby={labelledBy}
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={showList && highlight >= 0 ? `${listId}-${highlight}` : undefined}
        />
        {showList && (
          <ul id={listId} className="tag-input-suggestions" role="listbox">
            {matches.map((tag, i) => (
              <li
                key={tag}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === highlight}
                className={i === highlight ? 'is-highlighted' : ''}
                // Before the input's blur, which would add what's typed.
                onMouseDown={e => { e.preventDefault(); addTags([tag]); }}
                onMouseEnter={() => setHighlight(i)}
              >
                {tag}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default TagInput;
