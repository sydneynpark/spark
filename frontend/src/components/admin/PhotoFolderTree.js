import { useState, useEffect, useCallback, useRef } from 'react';
import ApiService from '../../services/api';
import { monthName } from '../../utils/photoDate';

export function folderLabel(name, kind) {
  return kind === 'month' && monthName(name) !== name ? `${name} · ${monthName(name)}` : name;
}

// The prefixes of `prefix` and every folder above it, root ('') first:
// '2026/05/' gives ['', '2026/', '2026/05/'].
export function prefixesDownTo(prefix) {
  const segments = prefix.split('/').filter(Boolean);
  return ['', ...segments.map((_, i) => `${segments.slice(0, i + 1).join('/')}/`)];
}

// One photo collection's folder listings (as the API's /admin/photos/folders
// gives them), fetched as they're needed and kept, by prefix, so the tree
// and whatever shows the selected folder share them. A listing that failed
// to load is { error }. Remount (key it by collection) to switch collection.
export function usePhotoFolders(collection) {
  const [listings, setListings] = useState({});
  // Fetched or being fetched, so expanding a folder twice fetches it once.
  const requested = useRef(new Set());

  const load = useCallback((prefix, { force = false } = {}) => {
    if (!force && requested.current.has(prefix)) return;
    requested.current.add(prefix);
    ApiService.fetchPhotoFolder(collection, prefix)
      .then(data => setListings(prev => ({ ...prev, [prefix]: data })))
      .catch(err => {
        // So it's tried again the next time it's wanted.
        requested.current.delete(prefix);
        setListings(prev => ({ ...prev, [prefix]: { error: err.message } }));
      });
  }, [collection]);

  const reload = useCallback(prefix => load(prefix, { force: true }), [load]);

  // Change a loaded listing in place, e.g. to drop a photo just deleted.
  const update = useCallback((prefix, change) => {
    setListings(prev => (prev[prefix] && !prev[prefix].error ? { ...prev, [prefix]: change(prev[prefix]) } : prev));
  }, []);

  return { listings, load, reload, update };
}

function FolderNode({ prefix, label, isLeaf, tree }) {
  const { listings, expanded, toggle, selected, onSelect, disabled } = tree;
  const open = !isLeaf && expanded.has(prefix);
  const listing = listings[prefix];
  const isSelected = selected === prefix;

  // Date folders newest first; anything else (like archive/) as listed.
  const children = listing && !listing.error
    ? (listing.child_folder_kind ? [...listing.folders].reverse() : listing.folders)
    : [];

  return (
    <li>
      <div className={`admin-folder-row${isSelected ? ' is-selected' : ''}`}>
        {isLeaf ? (
          <span className="admin-folder-toggle" aria-hidden="true" />
        ) : (
          <button
            type="button"
            className={`admin-folder-toggle${open ? ' is-open' : ''}`}
            aria-expanded={open}
            aria-label={`${open ? 'Collapse' : 'Expand'} ${label}`}
            onClick={() => toggle(prefix)}
          >
            <span className="admin-folder-caret" aria-hidden="true" />
          </button>
        )}
        <button
          type="button"
          className="admin-folder-name"
          aria-current={isSelected ? 'true' : undefined}
          onClick={() => onSelect(prefix)}
          disabled={disabled}
        >
          {label}
        </button>
      </div>

      {open && (
        <ul>
          {!listing && <li className="admin-folder-status">Loading...</li>}
          {listing?.error && <li className="admin-folder-status error">{listing.error}</li>}
          {listing && !listing.error && children.length === 0 && (
            <li className="admin-folder-status">No folders</li>
          )}
          {children.map(name => (
            <FolderNode
              key={name}
              prefix={`${prefix}${name}/`}
              label={folderLabel(name, listing.child_folder_kind)}
              // Inside YYYY/MM/DD/, nothing goes in a day folder but photos.
              isLeaf={listing.child_folder_kind === 'day'}
              tree={tree}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

// A collection's folders as a tree, each opening to the next level down
// with its triangle, and selected (to show what's in it) by its name. The
// selected folder, and every folder above it, start out open.
function PhotoFolderTree({ folders, rootLabel, selected, onSelect, disabled = false }) {
  const { listings, load } = folders;
  const [expanded, setExpanded] = useState(() => new Set(['']));

  useEffect(() => {
    const path = prefixesDownTo(selected);
    path.forEach(prefix => load(prefix));
    setExpanded(prev => (path.every(prefix => prev.has(prefix)) ? prev : new Set([...prev, ...path])));
  }, [selected, load]);

  function toggle(prefix) {
    const opening = !expanded.has(prefix);
    if (opening) load(prefix);
    setExpanded(prev => {
      const next = new Set(prev);
      if (opening) next.add(prefix); else next.delete(prefix);
      return next;
    });
  }

  const tree = { listings, expanded, toggle, selected, onSelect, disabled };
  return (
    <ul className="admin-folder-tree" aria-label="Folders">
      <FolderNode prefix="" label={rootLabel} isLeaf={false} tree={tree} />
    </ul>
  );
}

export default PhotoFolderTree;
