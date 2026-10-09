import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import ApiService from '../../services/api';
import { monthName } from '../../utils/photoDate';

// How many photos upload to S3 at once.
const UPLOAD_CONCURRENCY = 3;

const NEW_FOLDER_PLACEHOLDERS = { year: 'e.g. 2026', month: '1-12', day: '1-31' };

// Lightroom exports are named like "2025-05-17 074801 - Purple Martin.jpg",
// so a filename's leading date says which day folder it belongs in.
const FILENAME_DATE = /^(\d{4})-(\d{2})-(\d{2})/;

let nextId = 0;

function formatSize(bytes) {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function folderLabel(name, kind) {
  return kind === 'month' && monthName(name) !== name ? `${name} · ${monthName(name)}` : name;
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

function PhotoUploader() {
  const [searchParams, setSearchParams] = useSearchParams();
  const prefix = searchParams.get('folder') || '';
  const [listing, setListing] = useState(null);
  const [refreshCount, setRefreshCount] = useState(0);
  const [error, setError] = useState(null);
  const [newFolderName, setNewFolderName] = useState('');
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [files, setFiles] = useState([]); // { id, file, status, progress, error }
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    ApiService.fetchPhotoFolder(prefix)
      .then(data => { if (!cancelled) setListing(data); })
      .catch(err => {
        if (cancelled) return;
        setListing(null);
        setError(err.message);
      });
    return () => { cancelled = true; };
  }, [prefix, refreshCount]);

  // Until the folder that's open has loaded, rather than the last one.
  const current = listing && listing.prefix === prefix ? listing : null;
  const segments = prefix.split('/').filter(Boolean);
  const crumbs = [
    { label: 'Photos', prefix: '' },
    ...segments.map((segment, i) => ({ label: segment, prefix: `${segments.slice(0, i + 1).join('/')}/` })),
  ];
  const folderDate = segments.join('-');
  const toUpload = files.filter(f => f.status === 'pending' || f.status === 'error');

  function openFolder(target) {
    setNewFolderName('');
    setSearchParams(target ? { folder: target } : {});
  }

  async function handleCreateFolder(e) {
    e.preventDefault();
    setError(null);
    setCreatingFolder(true);
    try {
      const created = await ApiService.createPhotoFolder(prefix, newFolderName);
      openFolder(created.prefix);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreatingFolder(false);
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
          await ApiService.uploadPhoto(folder, item.file, progress => updateFile(item.id, { progress }));
          updateFile(item.id, { status: 'done', progress: 1 });
        } catch (err) {
          updateFile(item.id, { status: 'error', error: err.message });
        }
      }
    }

    await Promise.all(Array.from({ length: Math.min(UPLOAD_CONCURRENCY, queue.length) }, uploadNext));
    setUploading(false);
    setRefreshCount(count => count + 1);
  }

  return (
    <div className="admin-page admin-photo-upload-page">
      <Link to="/admin" className="back-link">← Back to Admin</Link>
      <h2>Upload Bird Photos</h2>
      <p className="admin-form-hint">
        Photos are filed by the day they were taken, in YYYY/MM/DD folders. Open that day's folder -- creating it, if it's new -- to upload into it.
      </p>

      {error && <p className="error">{error}</p>}

      <div className="admin-form">
        <nav className="admin-photo-breadcrumb" aria-label="Folder">
          {crumbs.map((crumb, i) => (
            <span key={crumb.prefix}>
              {i > 0 && <span className="admin-photo-breadcrumb-separator">/</span>}
              {i === crumbs.length - 1
                ? <span className="admin-photo-breadcrumb-current">{crumb.label}</span>
                : <button type="button" onClick={() => openFolder(crumb.prefix)} disabled={uploading}>{crumb.label}</button>}
            </span>
          ))}
        </nav>

        {!current && !error && <p className="admin-form-hint">Loading...</p>}

        {current && (
          <>
            {current.folders.length > 0 && (
              <div className="admin-photo-folders">
                {current.folders.map(name => (
                  <button
                    key={name}
                    type="button"
                    className="admin-photo-folder"
                    onClick={() => openFolder(`${prefix}${name}/`)}
                    disabled={uploading}
                  >
                    {folderLabel(name, current.child_folder_kind)}
                  </button>
                ))}
              </div>
            )}

            {current.child_folder_kind && (
              <>
                {current.folders.length === 0 && <p className="admin-form-hint">No folders here yet.</p>}
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
                  <button type="submit" className="admin-add-button" disabled={creatingFolder}>
                    {creatingFolder ? 'Creating...' : 'Create & Open'}
                  </button>
                </form>
              </>
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
                          <span>{photo.name}</span>
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
                    Uploaded photos are processed in the background (species from their keywords, plus a thumbnail), and show up on the site a few seconds later.
                  </p>
                </section>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default PhotoUploader;
