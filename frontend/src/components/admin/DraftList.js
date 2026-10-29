import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import ApiService from '../../services/api';
import { usePageTitle } from '../../utils/pageTitle';

function formatSaved(isoString) {
  return new Date(isoString).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
  });
}

function DraftList() {
  usePageTitle('Blog Drafts');
  // A post the editor just published, to link to.
  const published = useLocation().state?.published;
  const [drafts, setDrafts] = useState(null);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    ApiService.fetchDrafts()
      .then(data => { if (!cancelled) setDrafts(data); })
      .catch(err => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; };
  }, []);

  async function handleDelete(draft) {
    if (!window.confirm(`Delete "${draft.title || 'Untitled'}", and any photos uploaded to it? This can't be undone.`)) return;
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

  return (
    <div className="admin-page admin-drafts-page">
      <Link to="/admin" className="back-link">← Back to Admin</Link>
      <div className="admin-dashboard-header">
        <h2>Blog Drafts</h2>
        <Link className="admin-submit-button" to="/admin/posts/new">New Post</Link>
      </div>

      {published && (
        <p className="admin-success">
          Published <Link to={`/blog/${encodeURIComponent(published.slug)}`}>{published.title}</Link>.
          {published.photos.length > 0 && ' Its photos are being processed, and show up on the site a few seconds later.'}
        </p>
      )}
      {error && <p className="error">{error}</p>}

      {!drafts && !error && <p className="admin-form-hint">Loading...</p>}
      {drafts && drafts.length === 0 && <p className="admin-form-hint">No drafts. Start one with New Post.</p>}
      {drafts && drafts.length > 0 && (
        <ul className="admin-draft-list">
          {drafts.map(draft => (
            <li key={draft.id} className="admin-draft">
              <Link to={`/admin/posts/${draft.id}`} className="admin-draft-link">
                <span className="admin-draft-title">{draft.title || 'Untitled'}</span>
                <span className="admin-form-hint">
                  {draft.date ? `For ${draft.date}` : 'No date yet'} · Saved {formatSaved(draft.last_modified)}
                </span>
              </Link>
              <button
                type="button"
                className="admin-remove-button"
                onClick={() => handleDelete(draft)}
                disabled={deletingId === draft.id}
              >
                {deletingId === draft.id ? 'Deleting...' : 'Delete'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default DraftList;
