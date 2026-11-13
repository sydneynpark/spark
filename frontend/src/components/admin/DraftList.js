import { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import ApiService from '../../services/api';
import { usePageTitle } from '../../utils/pageTitle';

function formatSaved(isoString) {
  return new Date(isoString).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
  });
}

// The drafts, of new posts and of changes to published ones, and the
// published posts, to edit. ?edit=<post key> (as a post's Edit link opens
// it with) goes straight to editing that post.
function DraftList() {
  usePageTitle('Blog Posts');
  const navigate = useNavigate();
  // A post the editor just published, to link to.
  const published = useLocation().state?.published;
  const [searchParams] = useSearchParams();
  const editKey = searchParams.get('edit');
  const [drafts, setDrafts] = useState(null);
  const [posts, setPosts] = useState(null);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [openingKey, setOpeningKey] = useState(null);
  // The ?edit= key already opened: StrictMode runs effects twice, and each
  // run would start a draft.
  const openedEditKey = useRef(null);

  useEffect(() => {
    let cancelled = false;
    ApiService.fetchDrafts()
      .then(data => { if (!cancelled) setDrafts(data); })
      .catch(err => { if (!cancelled) setError(err.message); });
    ApiService.fetchPosts()
      .then(data => { if (!cancelled) setPosts(data); })
      .catch(err => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!editKey || openedEditKey.current === editKey) return;
    openedEditKey.current = editKey;
    handleEdit(editKey, { replace: true });
  }, [editKey]);

  async function handleEdit(key, navigateOptions) {
    setError(null);
    setOpeningKey(key);
    try {
      const draft = await ApiService.editPost(key);
      navigate(`/admin/posts/${draft.id}`, navigateOptions);
    } catch (err) {
      setError(err.message);
      setOpeningKey(null);
    }
  }

  async function handleDelete(draft) {
    const question = draft.editing
      ? `Discard your changes to "${draft.title || 'Untitled'}", and any photos uploaded with them? The published post stays as it is.`
      : `Delete "${draft.title || 'Untitled'}", and any photos uploaded to it? This can't be undone.`;
    if (!window.confirm(question)) return;
    setError(null);
    setDeletingId(draft.id);
    try {
      await ApiService.deleteDraft(draft.id);
      setDrafts(prev => prev.filter(d => d.id !== draft.id));
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingId(null);
    }
  }

  // The draft of changes to each post being edited, by the post's key.
  const editDrafts = Object.fromEntries((drafts || []).filter(d => d.editing).map(d => [d.editing.key, d]));

  return (
    <div className="admin-page admin-drafts-page">
      <Link to="/admin" className="back-link">← Back to Admin</Link>
      <div className="admin-dashboard-header">
        <h2>Blog Posts</h2>
        <Link className="admin-submit-button" to="/admin/posts/new">New Post</Link>
      </div>

      {published && (
        <p className="admin-success">
          {published.edited ? 'Published your changes to ' : 'Published '}
          <Link to={`/blog/${encodeURIComponent(published.slug)}`}>{published.title}</Link>.
          {published.photos.length > 0 && ' Its photos are being processed, and show up on the site a few seconds later.'}
        </p>
      )}
      {error && <p className="error">{error}</p>}
      {editKey && !error && <p className="admin-form-hint">Opening the post to edit...</p>}

      <h3 className="admin-drafts-heading">Drafts</h3>
      {!drafts && !error && <p className="admin-form-hint">Loading...</p>}
      {drafts && drafts.length === 0 && <p className="admin-form-hint">No drafts. Start one with New Post, or edit a published post.</p>}
      {drafts && drafts.length > 0 && (
        <ul className="admin-draft-list">
          {drafts.map(draft => (
            <li key={draft.id} className="admin-draft">
              <Link to={`/admin/posts/${draft.id}`} className="admin-draft-link">
                <span className="admin-draft-title">{draft.title || 'Untitled'}</span>
                <span className="admin-form-hint">
                  {draft.editing ? `Changes to /blog/${draft.editing.slug}` : draft.date ? `For ${draft.date}` : 'No date yet'}
                  {' · '}Saved {formatSaved(draft.last_modified)}
                </span>
              </Link>
              <button
                type="button"
                className="admin-remove-button"
                onClick={() => handleDelete(draft)}
                disabled={deletingId === draft.id}
              >
                {deletingId === draft.id ? 'Deleting...' : draft.editing ? 'Discard' : 'Delete'}
              </button>
            </li>
          ))}
        </ul>
      )}

      <h3 className="admin-drafts-heading">Published</h3>
      {!posts && !error && <p className="admin-form-hint">Loading...</p>}
      {posts && posts.length === 0 && <p className="admin-form-hint">Nothing published yet.</p>}
      {posts && posts.length > 0 && (
        <ul className="admin-draft-list">
          {posts.map(post => (
            <li key={post.key} className="admin-draft">
              <Link to={`/blog/${encodeURIComponent(post.slug)}`} className="admin-draft-link">
                <span className="admin-draft-title">{post.title}</span>
                <span className="admin-form-hint">{post.date} · /blog/{post.slug}</span>
              </Link>
              {editDrafts[post.key] ? (
                <Link className="admin-back-button admin-draft-action" to={`/admin/posts/${editDrafts[post.key].id}`}>
                  Continue Editing
                </Link>
              ) : (
                <button
                  type="button"
                  className="admin-back-button admin-draft-action"
                  onClick={() => handleEdit(post.key)}
                  disabled={openingKey !== null}
                >
                  {openingKey === post.key ? 'Opening...' : 'Edit'}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default DraftList;
