import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import ApiService from '../../services/api';
import PostContent, { PostDates } from '../PostContent';
import { monthName } from '../../utils/photoDate';
import { usePageTitle } from '../../utils/pageTitle';
import { tagsInUse } from '../../utils/postTags';
import TagInput from '../TagInput';

// How many photos upload to S3 at once, as in PhotoUploader.
const UPLOAD_CONCURRENCY = 3;

// The photo collections a draft's photos are published to (see the API's
// PHOTO_COLLECTIONS), and the folder each is in in the photos bucket.
const COLLECTIONS = {
  birds: { label: 'Bird photos', folder: 'birds/' },
  photos: { label: 'Other photos', folder: 'photos/' },
};

// Every photo:// reference in some markdown, as the API finds them.
const PHOTO_REF = /photo:\/\/([^`)\n]+)/g;

// All strings, but tags, a list of them.
const EMPTY_FIELDS = { title: '', date: '', written: '', tags: [], preview: '', photo: '', content: '' };

let nextUploadId = 0;

function todayIso() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function draftFields(draft) {
  return Object.fromEntries(Object.keys(EMPTY_FIELDS).map(name => [name, draft[name] || EMPTY_FIELDS[name]]));
}

function sameFields(a, b) {
  return Object.keys(EMPTY_FIELDS).every(name => (name === 'tags'
    ? a.tags.join('\n') === b.tags.join('\n')
    : a[name] === b[name]));
}

function photoRefs(markdown) {
  return Array.from(markdown.matchAll(PHOTO_REF), match => `photo://${match[1].trim()}`);
}

function refFilename(ref) {
  return ref.split('/').pop();
}

function folderLabel(name, kind) {
  return kind === 'month' && monthName(name) !== name ? `${name} · ${monthName(name)}` : name;
}

// Browses the photos already on the site, as PhotoUploader does, to embed
// one in the post.
function ExistingPhotoPicker({ onInsert }) {
  const [collection, setCollection] = useState('birds');
  const [prefix, setPrefix] = useState('');
  const [listing, setListing] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    ApiService.fetchPhotoFolder(collection, prefix)
      .then(data => { if (!cancelled) setListing({ ...data, collection }); })
      .catch(err => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; };
  }, [collection, prefix]);

  const current = listing && listing.collection === collection && listing.prefix === prefix ? listing : null;
  const segments = prefix.split('/').filter(Boolean);
  const crumbs = [
    { label: COLLECTIONS[collection].label, prefix: '' },
    ...segments.map((segment, i) => ({ label: segment, prefix: `${segments.slice(0, i + 1).join('/')}/` })),
  ];

  function chooseCollection(name) {
    setCollection(name);
    setPrefix('');
  }

  return (
    <div className="admin-existing-photos">
      <div className="admin-editor-choice">
        {Object.entries(COLLECTIONS).map(([name, { label }]) => (
          <label key={name} className="admin-checkbox-label">
            <input type="radio" checked={collection === name} onChange={() => chooseCollection(name)} />
            {label}
          </label>
        ))}
      </div>

      <nav className="admin-photo-breadcrumb" aria-label="Folder">
        {crumbs.map((crumb, i) => (
          <span key={crumb.prefix}>
            {i > 0 && <span className="admin-photo-breadcrumb-separator">/</span>}
            {i === crumbs.length - 1
              ? <span className="admin-photo-breadcrumb-current">{crumb.label}</span>
              : <button type="button" onClick={() => setPrefix(crumb.prefix)}>{crumb.label}</button>}
          </span>
        ))}
      </nav>

      {error && <p className="error">{error}</p>}
      {!current && !error && <p className="admin-form-hint">Loading...</p>}
      {current && (
        <>
          {current.folders.length > 0 && (
            <div className="admin-photo-folders">
              {current.folders.map(name => (
                <button key={name} type="button" className="admin-photo-folder" onClick={() => setPrefix(`${prefix}${name}/`)}>
                  {folderLabel(name, current.child_folder_kind)}
                </button>
              ))}
            </div>
          )}
          {current.photos.length > 0 && (
            <ul className="admin-editor-photo-grid">
              {current.photos.map(photo => (
                <li key={photo.name}>
                  <button
                    type="button"
                    title={`Insert ${photo.name}`}
                    onClick={() => onInsert(`photo://${photo.s3_uri.replace(/^s3:\/\/[^/]+\//, '')}`)}
                  >
                    <img
                      src={ApiService.getThumbnailUrl(photo.s3_uri)}
                      alt=""
                      loading="lazy"
                      onError={e => { e.target.src = '/images/placeholder-unknown.jpg'; }}
                    />
                    <span>{photo.name}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {current.folders.length === 0 && current.photos.length === 0 && (
            <p className="admin-form-hint">Nothing in this folder.</p>
          )}
        </>
      )}
    </div>
  );
}

function PostEditor() {
  const navigate = useNavigate();
  const { draftId: routeId } = useParams();
  // The draft being edited: none for a new post until it's first saved,
  // when the URL changes to its ID (without reloading it).
  const [initialId] = useState(routeId === 'new' ? null : routeId);
  const [draftId, setDraftId] = useState(initialId);
  const [fields, setFields] = useState(() => ({ ...EMPTY_FIELDS, date: todayIso() }));
  const [savedFields, setSavedFields] = useState(EMPTY_FIELDS);
  const [loading, setLoading] = useState(initialId !== null);
  const [loadError, setLoadError] = useState(null);
  const [tab, setTab] = useState('write');
  const [photos, setPhotos] = useState([]);
  const [uploadCollection, setUploadCollection] = useState('birds');
  const [uploads, setUploads] = useState([]); // { id, name, status, progress, error }
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  // For a draft of changes to a published post, which: { key, slug }.
  const [editing, setEditing] = useState(null);
  // The tags published posts have, to suggest.
  const [tagSuggestions, setTagSuggestions] = useState([]);
  const textareaRef = useRef(null);
  const saveRef = useRef(null);

  usePageTitle(fields.title ? `Editing ${fields.title}` : 'New Post');
  const dirty = !sameFields(fields, savedFields);
  const uploading = uploads.some(u => u.status === 'uploading');
  const busy = saving || publishing;

  useEffect(() => {
    let cancelled = false;
    // Just suggestions: without them, tags can still be typed.
    ApiService.fetchPosts()
      .then(posts => { if (!cancelled) setTagSuggestions(tagsInUse(posts).map(({ tag }) => tag)); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!initialId) return;
    let cancelled = false;
    Promise.all([ApiService.fetchDraft(initialId), ApiService.fetchDraftPhotos(initialId)])
      .then(([draft, draftPhotos]) => {
        if (cancelled) return;
        const loaded = draftFields(draft);
        setFields(loaded);
        setSavedFields(loaded);
        setEditing(draft.editing || null);
        setPhotos(draftPhotos);
      })
      .catch(err => { if (!cancelled) setLoadError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [initialId]);

  // Unsaved changes are lost on leaving the page, so the browser asks first.
  useEffect(() => {
    if (!dirty) return undefined;
    const handleBeforeUnload = e => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [dirty]);

  // Cmd/Ctrl+S saves.
  useEffect(() => {
    const handleKeyDown = e => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        saveRef.current();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  function setField(name, value) {
    setFields(prev => ({ ...prev, [name]: value }));
  }

  async function refreshPhotos(id = draftId) {
    if (!id) return;
    try {
      setPhotos(await ApiService.fetchDraftPhotos(id));
    } catch (err) {
      setError(err.message);
    }
  }

  // Saves the draft, creating it if it's new, and returns its ID.
  async function save() {
    const snapshot = fields;
    const saved = draftId
      ? await ApiService.saveDraft(draftId, snapshot)
      : await ApiService.createDraft(snapshot);
    if (!draftId) {
      setDraftId(saved.id);
      navigate(`/admin/posts/${saved.id}`, { replace: true });
    }
    setSavedFields(snapshot);
    return saved.id;
  }

  async function handleSave() {
    if (busy) return;
    setError(null);
    setNotice(null);
    setSaving(true);
    try {
      await save();
      setNotice('Draft saved.');
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }
  saveRef.current = handleSave;

  // Puts a photo's embed at the cursor (or the end, from the preview tab),
  // as a paragraph of its own -- or, right after another embed, on the next
  // line, which joins its row of tiles.
  function insertEmbed(ref) {
    const embed = `\`${ref}\``;
    const textarea = textareaRef.current;
    setFields(prev => {
      const at = textarea ? textarea.selectionEnd : prev.content.length;
      const before = prev.content.slice(0, at);
      const after = prev.content.slice(at);
      const afterEmbed = /`photo:\/\/[^`\n]*`\n?$/.test(before);
      const lead = before === '' || before.endsWith('\n\n') ? ''
        : before.endsWith('\n') ? (afterEmbed ? '' : '\n')
        : afterEmbed ? '\n' : '\n\n';
      const trail = after.startsWith('\n\n') ? '' : after.startsWith('\n') ? '\n' : after === '' ? '\n' : '\n\n';
      const cursor = before.length + lead.length + embed.length + trail.length;
      if (textarea) {
        requestAnimationFrame(() => {
          textarea.focus();
          textarea.setSelectionRange(cursor, cursor);
        });
      }
      return { ...prev, content: before + lead + embed + trail + after };
    });
  }

  function updateUpload(id, changes) {
    setUploads(prev => prev.map(u => (u.id === id ? { ...u, ...changes } : u)));
  }

  async function handleFilesChosen(e) {
    const files = Array.from(e.target.files);
    // Lets the same files be chosen again.
    e.target.value = '';
    if (files.length === 0) return;
    setError(null);
    setNotice(null);

    let id = draftId;
    if (!id) {
      // Photos are uploaded into the draft, so it has to exist first.
      try {
        id = await save();
      } catch (err) {
        setError(err.message);
        return;
      }
    }

    const collection = uploadCollection;
    const queue = files.map(file => {
      nextUploadId += 1;
      return { id: nextUploadId, file };
    });
    setUploads(prev => [
      ...prev.filter(u => u.status !== 'done'),
      ...queue.map(item => ({ id: item.id, name: item.file.name, status: 'uploading', progress: 0, error: null })),
    ]);

    async function uploadNext() {
      while (queue.length > 0) {
        const item = queue.shift();
        try {
          await ApiService.uploadDraftPhoto(id, collection, item.file, progress => updateUpload(item.id, { progress }));
          updateUpload(item.id, { status: 'done', progress: 1 });
          insertEmbed(`photo://drafts/${id}/${collection}/${item.file.name}`);
        } catch (err) {
          updateUpload(item.id, { status: 'error', error: err.message });
        }
      }
    }

    await Promise.all(Array.from({ length: Math.min(UPLOAD_CONCURRENCY, queue.length) }, uploadNext));
    await refreshPhotos(id);
  }

  async function handleRemovePhoto(photo) {
    const embedded = photoRefs(fields.content).includes(photo.ref);
    const message = embedded
      ? `${photo.filename} is embedded in the post. Remove it anyway? You'll need to delete its embed too, before publishing.`
      : `Remove ${photo.filename} from this draft?`;
    if (!window.confirm(message)) return;
    setError(null);
    try {
      await ApiService.deleteDraftPhoto(draftId, photo.key);
      if (fields.photo === photo.ref) setField('photo', '');
      setPhotos(prev => prev.filter(p => p.key !== photo.key));
    } catch (err) {
      setError(err.message);
    }
  }

  function handleTab(name) {
    setTab(name);
    // Their view URLs only last a few hours.
    if (name === 'preview') refreshPhotos();
  }

  async function handlePublish() {
    setError(null);
    setNotice(null);
    if (!fields.title.trim() || !fields.date) {
      setError('Give the post a title and date before publishing it.');
      return;
    }
    const photoNote = photos.length > 0
      ? ` Its ${photos.length} uploaded photo${photos.length === 1 ? '' : 's'} will be added to the site's photos too, filed under ${fields.date}.`
      : '';
    const writtenNote = fields.written && fields.written !== fields.date ? `, written ${fields.written}` : '';
    const question = editing
      ? `Replace the published post at /blog/${editing.slug} with these changes now?`
      : `Publish "${fields.title.trim()}" on the site now, dated ${fields.date}${writtenNote}?`;
    if (!window.confirm(`${question}${photoNote}`)) return;

    setPublishing(true);
    try {
      const id = await save();
      const result = await ApiService.publishDraft(id);
      // Nothing's left to lose: the draft is gone.
      setSavedFields(fields);
      navigate('/admin/posts', { state: { published: { ...result, title: fields.title.trim(), edited: !!editing } } });
    } catch (err) {
      setError(err.message);
      setPublishing(false);
    }
  }

  async function handleDelete() {
    const question = editing
      ? 'Discard these changes, and any photos uploaded with them? The published post stays as it is.'
      : 'Delete this draft, and any photos uploaded to it? This can\'t be undone.';
    if (!window.confirm(question)) return;
    setError(null);
    try {
      if (draftId) await ApiService.deleteDraft(draftId);
      setSavedFields(fields);
      navigate('/admin/posts');
    } catch (err) {
      setError(err.message);
    }
  }

  function handleBack(e) {
    if (dirty && !window.confirm('Leave without saving your changes?')) e.preventDefault();
  }

  if (loading) return <div className="admin-page"><p>Loading...</p></div>;
  if (loadError) {
    return (
      <div className="admin-page">
        <Link to="/admin/posts" className="back-link">← Back to Drafts</Link>
        <p className="error">{loadError}</p>
      </div>
    );
  }

  const photoUrls = Object.fromEntries(photos.map(photo => [photo.key, photo.url]));
  // What the post's thumbnail can be: any photo it embeds, or that's been
  // uploaded to it, and whatever it already is.
  const thumbnailOptions = Array.from(new Set([
    ...photoRefs(fields.content),
    ...photos.map(photo => photo.ref),
    ...(fields.photo ? [fields.photo] : []),
  ]));
  const thumbnailKey = fields.photo.replace(/^photo:\/\//, '');
  const thumbnailSrc = fields.photo
    && (photoUrls[thumbnailKey] || ApiService.getThumbnailUrl(`s3://spark.wiki.photos/${thumbnailKey}`));

  return (
    <div className="admin-page admin-post-editor-page">
      <Link to="/admin/posts" className="back-link" onClick={handleBack}>← Back to Blog Posts</Link>
      <h2>{editing ? 'Edit Post' : draftId ? 'Edit Draft' : 'New Post'}</h2>
      {editing && (
        <p className="admin-editing-note">
          These are changes to the published post at{' '}
          <Link to={`/blog/${encodeURIComponent(editing.slug)}`}>/blog/{editing.slug}</Link>. It stays as it is
          until you publish them, which replaces it, keeping its URL. Until then, they're saved as a draft.
        </p>
      )}

      {error && <p className="error">{error}</p>}
      {notice && !dirty && <p className="admin-success">{notice}</p>}

      <div className="admin-form">
        <div className="admin-form-row admin-post-fields">
          <label>
            Title
            <input type="text" value={fields.title} onChange={e => setField('title', e.target.value)} />
          </label>
          <label>
            Date
            <input type="date" value={fields.date} onChange={e => setField('date', e.target.value)} />
          </label>
          <label>
            <span>
              Date Written <span className="admin-form-hint">(optional)</span>
              {fields.written && (
                <button type="button" className="admin-link-button" onClick={() => setField('written', '')}>Clear</button>
              )}
            </span>
            <input type="date" value={fields.written} onChange={e => setField('written', e.target.value)} />
          </label>
        </div>
        <p className="admin-form-hint admin-post-dates-hint">
          The post is shown under its date, and its photos are filed under it. Writing about something past, like a
          trip? Give the trip's date, and when you wrote it as the date written. Left empty, that's the same as the date.
        </p>

        <div className="admin-editor-tabs" role="tablist">
          {['write', 'preview'].map(name => (
            <button
              key={name}
              type="button"
              role="tab"
              aria-selected={tab === name}
              className={tab === name ? 'is-active' : ''}
              onClick={() => handleTab(name)}
            >
              {name === 'write' ? 'Write' : 'Preview'}
            </button>
          ))}
        </div>

        {tab === 'write' ? (
          <textarea
            ref={textareaRef}
            className="admin-editor-textarea"
            value={fields.content}
            onChange={e => setField('content', e.target.value)}
            rows={22}
            placeholder="Write in Markdown. Photos embed as `photo://<key>`, on a line of their own -- upload or pick one below to insert it here."
          />
        ) : (
          <article className="blog-post admin-post-preview">
            <header className="post-header">
              <h1>{fields.title || 'Untitled'}</h1>
              <PostDates date={fields.date} written={fields.written} />
            </header>
            {fields.content.trim()
              ? <PostContent content={fields.content} photoUrls={photoUrls} />
              : <div className="post-content"><p className="admin-form-hint">Nothing to preview yet.</p></div>}
          </article>
        )}

        <section className="admin-form-section">
          <h3>Photos</h3>
          <p className="admin-form-hint">
            Photos uploaded here stay with the draft until it's published. Then they're added to the site's bird photos or other photos, filed under the post's date.
          </p>
          <div className="admin-editor-upload">
            <div className="admin-editor-choice">
              {Object.entries(COLLECTIONS).map(([name, { label }]) => (
                <label key={name} className="admin-checkbox-label">
                  <input
                    type="radio"
                    checked={uploadCollection === name}
                    onChange={() => setUploadCollection(name)}
                    disabled={uploading}
                  />
                  {label}
                </label>
              ))}
            </div>
            <label className={`admin-photo-picker${uploading || busy ? ' is-disabled' : ''}`}>
              Upload JPEGs...
              <input type="file" accept=".jpg,.jpeg,image/jpeg" multiple onChange={handleFilesChosen} disabled={uploading || busy} />
            </label>
          </div>

          {uploads.length > 0 && (
            <ul className="admin-photo-queue">
              {uploads.filter(u => u.status !== 'done').map(upload => (
                <li key={upload.id} className={`admin-photo-queue-item is-${upload.status}`}>
                  <div className="admin-editor-upload-row">
                    <span className="admin-photo-queue-name">{upload.name}</span>
                    <span className="admin-photo-queue-status">
                      {upload.status === 'error' ? 'Failed' : `${Math.round(upload.progress * 100)}%`}
                    </span>
                  </div>
                  {upload.status === 'uploading' && <progress value={upload.progress} max="1" />}
                  {upload.status === 'error' && <p className="admin-photo-queue-error">{upload.error}</p>}
                </li>
              ))}
            </ul>
          )}

          {photos.length > 0 && (
            <ul className="admin-photo-existing">
              {photos.map(photo => (
                <li key={photo.key}>
                  <img src={photo.url} alt="" loading="lazy" />
                  <span className="admin-editor-photo-name">
                    {photo.filename}
                    <span className="admin-form-hint"> · {COLLECTIONS[photo.collection]?.label || photo.collection}</span>
                  </span>
                  <button type="button" className="admin-add-button" onClick={() => insertEmbed(photo.ref)}>Insert</button>
                  <button type="button" className="admin-remove-button" onClick={() => handleRemovePhoto(photo)}>Remove</button>
                </li>
              ))}
            </ul>
          )}

          <details className="admin-editor-details">
            <summary>Insert a photo that's already on the site</summary>
            <ExistingPhotoPicker onInsert={insertEmbed} />
          </details>
        </section>

        <section className="admin-form-section">
          <h3>Blog Listing</h3>
          <div className="admin-editor-tags">
            <span id="admin-editor-tags-label">
              Tags <span className="admin-form-hint">(optional; the blog can be filtered by them)</span>
            </span>
            <TagInput
              tags={fields.tags}
              onChange={tags => setField('tags', tags)}
              suggestions={tagSuggestions}
              labelledBy="admin-editor-tags-label"
            />
          </div>
          <label>
            Preview Text <span className="admin-form-hint">(optional)</span>
            <textarea
              value={fields.preview}
              onChange={e => setField('preview', e.target.value)}
              rows={2}
              placeholder="Shown under the title on the blog page. Leave blank to use the start of the post."
            />
          </label>
          <div className="admin-editor-thumbnail">
            <label>
              Thumbnail
              <select value={fields.photo} onChange={e => setField('photo', e.target.value)}>
                <option value="">The post's first photo</option>
                {thumbnailOptions.map(ref => (
                  <option key={ref} value={ref}>{refFilename(ref)}</option>
                ))}
              </select>
            </label>
            {thumbnailSrc && <img src={thumbnailSrc} alt="" />}
          </div>
        </section>

        <div className="admin-form-actions">
          <button type="button" className="admin-remove-button" onClick={handleDelete} disabled={busy}>
            {editing ? 'Discard Changes' : 'Delete Draft'}
          </button>
          <div className="admin-editor-actions">
            <span className="admin-form-hint">{dirty ? 'Unsaved changes' : draftId ? 'Saved' : ''}</span>
            <button type="button" className="admin-back-button" onClick={handleSave} disabled={busy}>
              {saving ? 'Saving...' : 'Save Draft'}
            </button>
            <button type="button" className="admin-submit-button" onClick={handlePublish} disabled={busy || uploading}>
              {publishing ? 'Publishing...' : editing ? 'Publish Changes' : 'Publish'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PostEditor;
