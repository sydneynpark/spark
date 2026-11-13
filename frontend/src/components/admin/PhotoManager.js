import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import ApiService from '../../services/api';
import { usePageTitle } from '../../utils/pageTitle';
import PhotoFolderTree, { folderLabel, prefixesDownTo, usePhotoFolders } from './PhotoFolderTree';

// How many photos upload to S3 at once.
const UPLOAD_CONCURRENCY = 3;

const NEW_FOLDER_PLACEHOLDERS = { year: 'e.g. 2026', month: '1-12', day: '1-31' };

// Lightroom exports are named like "2025-05-17 074801 - Purple Martin.jpg",
// so a filename's leading date says which day folder it belongs in.
const FILENAME_DATE = /^(\d{4})-(\d{2})-(\d{2})/;

// The photo collections this manages (see the API's PHOTO_COLLECTIONS).
const COLLECTIONS = {
  birds: {
    title: 'Bird Photos',
    folderName: 'birds',
    processing: 'species from their keywords, plus a thumbnail',
  },
  photos: {
    title: 'Photos',
    folderName: 'photos',
    processing: 'their dates, plus a thumbnail',
  },
};

let nextId = 0;

function formatSize(bytes) {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function statusLabel(item) {
  switch (item.status) {
    case 'uploading': return `${Math.round(item.progress * 100)}%`;
    case 'done': return 'Uploaded';
    case 'error': return 'Failed';
    default: return 'Ready';
  }
}

// Things worth a second look before uploading -- neither stops the upload.
function fileWarnings(file, listing, folderDate) {
  const warnings = [];
  if (listing.photos.some(photo => photo.name === file.name)) {
    warnings.push('Replaces the photo with this name already in this folder');
  }
  const match = FILENAME_DATE.exec(file.name);
  if (match) {
    const fileDate = `${match[1]}-${match[2]}-${match[3]}`;
    if (fileDate !== folderDate) {
      warnings.push(`Named for ${fileDate}, but this is the ${folderDate} folder`);
    }
  }
  return warnings;
}

// The selected folder's name, from the collection down: "birds / 2026 /
// 05 · May / 23".
function folderTitle(rootLabel, segments) {
  const kinds = ['year', 'month', 'day'];
  return [rootLabel, ...segments.map((segment, i) => folderLabel(segment, kinds[i]))].join(' / ');
}

// A photo collection's YYYY/MM/DD folders, as a tree to pick one from, and
// the one picked: to upload photos into, and delete photos (and empty
// folders) from.
function PhotoManager({ collection }) {
  const { title, folderName, processing } = COLLECTIONS[collection];
  usePageTitle(title);
  const [searchParams, setSearchParams] = useSearchParams();
  const prefix = searchParams.get('folder') || '';
  const folders = usePhotoFolders(collection);
  const [error, setError] = useState(null);
  const [newFolderName, setNewFolderName] = useState('');
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [files, setFiles] = useState([]); // { id, file, status, progress, error }
  const [uploading, setUploading] = useState(false);
  // The name of the photo being deleted, or '/' for the folder itself.
  const [deleting, setDeleting] = useState(null);
  const [notice, setNotice] = useState(null);

  // The selected folder's listing, once it's loaded (the tree loads it).
  const listing = folders.listings[prefix];
  const current = listing && !listing.error ? listing : null;
  const segments = prefix.split('/').filter(Boolean);
  const folderDate = segments.join('-');
  const toUpload = files.filter(f => f.status === 'pending' || f.status === 'error');

  const parentPrefix = segments.length > 1 ? `${segments.slice(0, -1).join('/')}/` : '';
  // An empty year, month, or day folder, which can be deleted.
  const canDeleteFolder = current && prefix !== '' && current.folders.length === 0 && current.photos.length === 0
    && (current.child_folder_kind || current.accepts_uploads);
  const busy = uploading || deleting !== null;

  function openFolder(target) {
    setNewFolderName('');
    setNotice(null);
    setError(null);
    setSearchParams(target ? { folder: target } : {});
  }

  async function handleCreateFolder(e) {
    e.preventDefault();
    setError(null);
    setCreatingFolder(true);
    try {
      const created = await ApiService.createPhotoFolder(collection, prefix, newFolderName);
      folders.reload(prefix);
      openFolder(created.prefix);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreatingFolder(false);
    }
  }

  async function handleDeletePhoto(photo) {
    if (!window.confirm(`Delete "${photo.name}" for good? It comes off the site too, and this can't be undone.`)) return;
    setError(null);
    setNotice(null);
    setDeleting(photo.name);
    try {
      await ApiService.deletePhoto(collection, prefix, photo.name);
      folders.update(prefix, prev => ({ ...prev, photos: prev.photos.filter(p => p.name !== photo.name) }));
      // A folder there only because of its photos is gone with the last one.
      if (current && current.photos.length === 1) {
        prefixesDownTo(parentPrefix).forEach(folders.reload);
      }
      setNotice(`Deleted "${photo.name}". It's off the site once that's been processed, in a few seconds.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setDeleting(null);
    }
  }

  async function handleDeleteFolder() {
    setError(null);
    setDeleting('/');
    try {
      await ApiService.deletePhotoFolder(collection, prefix);
      // The folders above it too, which may have been there only for it.
      prefixesDownTo(parentPrefix).forEach(folders.reload);
      openFolder(parentPrefix);
    } catch (err) {
      setError(err.message);
    } finally {
      setDeleting(null);
    }
  }

  function handleFilesChosen(e) {
    const chosen = Array.from(e.target.files).map(file => {
      nextId += 1;
      return { id: nextId, file, status: 'pending', progress: 0, error: null };
    });
    // Choosing a file again replaces the earlier pick of it.
    const chosenNames = new Set(chosen.map(item => item.file.name));
    setFiles(prev => [...prev.filter(item => !chosenNames.has(item.file.name)), ...chosen]);
    // Lets the same files be chosen again after removing them.
    e.target.value = '';
  }

  function updateFile(id, changes) {
    setFiles(prev => prev.map(item => (item.id === id ? { ...item, ...changes } : item)));
  }

  function removeFile(id) {
    setFiles(prev => prev.filter(item => item.id !== id));
  }

  async function handleUpload() {
    const folder = prefix;
    const queue = [...toUpload];
    setError(null);
    setUploading(true);

    async function uploadNext() {
      while (queue.length > 0) {
        const item = queue.shift();
        updateFile(item.id, { status: 'uploading', progress: 0, error: null });
        try {
          await ApiService.uploadPhoto(collection, folder, item.file, progress => updateFile(item.id, { progress }));
          updateFile(item.id, { status: 'done', progress: 1 });
        } catch (err) {
          updateFile(item.id, { status: 'error', error: err.message });
        }
      }
    }

    await Promise.all(Array.from({ length: Math.min(UPLOAD_CONCURRENCY, queue.length) }, uploadNext));
    setUploading(false);
    folders.reload(folder);
  }

  return (
    <div className="admin-page admin-photo-upload-page">
      <Link to="/admin" className="back-link">← Back to Admin</Link>
      <h2>{title}</h2>
      <p className="admin-form-hint">
        Photos are filed by the day they were taken, in YYYY/MM/DD folders. Pick that day's folder -- creating it, if it's new -- to upload into it, or to delete photos from it.
      </p>

      <div className="admin-photo-browser">
        <div className="admin-form admin-photo-tree-panel">
          <PhotoFolderTree
            folders={folders}
            rootLabel={folderName}
            selected={prefix}
            onSelect={openFolder}
            disabled={busy}
          />
        </div>

        <div className="admin-form admin-photo-folder-panel">
          <h3 className="admin-photo-folder-title">{folderTitle(folderName, segments)}</h3>

          {error && <p className="error">{error}</p>}
          {notice && <p className="admin-success">{notice}</p>}
          {listing?.error && <p className="error">{listing.error}</p>}
          {!listing && <p className="admin-form-hint">Loading...</p>}

          {current && (
            <>
              {current.child_folder_kind && (
                <form className="admin-photo-new-folder" onSubmit={handleCreateFolder}>
                  <label>
                    New {current.child_folder_kind} folder
                    <input
                      type="text"
                      inputMode="numeric"
                      value={newFolderName}
                      onChange={e => setNewFolderName(e.target.value)}
                      placeholder={NEW_FOLDER_PLACEHOLDERS[current.child_folder_kind]}
                      required
                    />
                  </label>
                  <button type="submit" className="admin-add-button" disabled={creatingFolder || busy}>
                    {creatingFolder ? 'Creating...' : 'Create & Open'}
                  </button>
                </form>
              )}

              {current.child_folder_kind && !canDeleteFolder && (
                <p className="admin-form-hint">Photos go in a day folder: open one in the tree, or create it.</p>
              )}

              {canDeleteFolder && (
                <div className="admin-photo-folder-actions">
                  <span className="admin-form-hint">This folder is empty.</span>
                  <button type="button" className="admin-remove-button" onClick={handleDeleteFolder} disabled={busy}>
                    {deleting === '/' ? 'Deleting...' : 'Delete Folder'}
                  </button>
                </div>
              )}

              {!current.child_folder_kind && !current.accepts_uploads && (
                <p className="admin-form-hint">This folder is outside the YYYY/MM/DD structure, so photos can't be uploaded here.</p>
              )}

              {current.accepts_uploads && (
                <>
                  <section className="admin-form-section">
                    <h3>In This Folder</h3>
                    {current.photos.length === 0 ? (
                      <p className="admin-form-hint">No photos yet.</p>
                    ) : (
                      <ul className="admin-photo-existing">
                        {current.photos.map(photo => (
                          <li key={photo.name}>
                            <img
                              src={ApiService.getThumbnailUrl(photo.s3_uri)}
                              alt=""
                              loading="lazy"
                              onError={e => { e.target.src = '/images/placeholder-unknown.jpg'; }}
                            />
                            <a href={ApiService.getFullsizeUrl(photo.s3_uri)} target="_blank" rel="noreferrer">{photo.name}</a>
                            <button
                              type="button"
                              className="admin-remove-button"
                              onClick={() => handleDeletePhoto(photo)}
                              disabled={busy}
                            >
                              {deleting === photo.name ? 'Deleting...' : 'Delete'}
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </section>

                  <section className="admin-form-section">
                    <h3>Upload</h3>
                    <label className={`admin-photo-picker${uploading ? ' is-disabled' : ''}`}>
                      Choose JPEGs...
                      <input type="file" accept=".jpg,.jpeg,image/jpeg" multiple onChange={handleFilesChosen} disabled={uploading} />
                    </label>

                    {files.length > 0 && (
                      <ul className="admin-photo-queue">
                        {files.map(item => (
                          <li key={item.id} className={`admin-photo-queue-item is-${item.status}`}>
                            <div className="admin-photo-queue-row">
                              <span className="admin-photo-queue-name">{item.file.name}</span>
                              <span className="admin-photo-queue-size">{formatSize(item.file.size)}</span>
                              <span className="admin-photo-queue-status">{statusLabel(item)}</span>
                              {!uploading && item.status !== 'done' && (
                                <button type="button" className="admin-remove-button" onClick={() => removeFile(item.id)}>Remove</button>
                              )}
                            </div>
                            {item.status === 'uploading' && <progress value={item.progress} max="1" />}
                            {item.status === 'error' && <p className="admin-photo-queue-error">{item.error}</p>}
                            {(item.status === 'pending' || item.status === 'error') &&
                              fileWarnings(item.file, current, folderDate).map(warning => (
                                <p key={warning} className="admin-photo-queue-warning">⚠ {warning}</p>
                              ))}
                          </li>
                        ))}
                      </ul>
                    )}

                    <div className="admin-form-actions">
                      <button
                        type="button"
                        className="admin-back-button"
                        onClick={() => setFiles([])}
                        disabled={uploading || files.length === 0}
                      >
                        Clear List
                      </button>
                      <button
                        type="button"
                        className="admin-submit-button"
                        onClick={handleUpload}
                        disabled={uploading || toUpload.length === 0}
                      >
                        {uploading ? 'Uploading...' : `Upload ${toUpload.length} Photo${toUpload.length === 1 ? '' : 's'}`}
                      </button>
                    </div>
                    <p className="admin-form-hint">
                      Uploaded photos are processed in the background ({processing}), and show up on the site a few seconds later.
                    </p>
                  </section>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default PhotoManager;
