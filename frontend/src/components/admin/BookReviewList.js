import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import ApiService from '../../services/api';
import { usePageTitle } from '../../utils/pageTitle';

// The public /books endpoint only returns its first 50 by default.
const BOOK_LIMIT = 1000;

function bookPath(title) {
  return `/books/${encodeURIComponent(title)}`;
}

// The book reviews, to start a new one or edit one, like the blog's
// DraftList: the same list the public Books page shows (most recently
// reviewed first).
function BookReviewList() {
  usePageTitle('Books');
  // A review the form just saved, to link to.
  const saved = useLocation().state?.saved;
  const [books, setBooks] = useState(null);
  const [filter, setFilter] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    ApiService.fetchBooks(BOOK_LIMIT)
      .then(data => { if (!cancelled) setBooks(data); })
      .catch(err => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; };
  }, []);

  const query = filter.trim().toLowerCase();
  const shown = (books || []).filter(book =>
    !query || book.title.toLowerCase().includes(query) || (book.author || '').toLowerCase().includes(query));

  return (
    <div className="admin-page admin-book-list-page">
      <Link to="/admin" className="back-link">← Back to Admin</Link>
      <div className="admin-dashboard-header">
        <h2>Books</h2>
        <Link className="admin-submit-button" to="/admin/books/new">New Review</Link>
      </div>

      {saved && (
        <p className="admin-success">
          {saved.edited ? 'Saved your changes to ' : 'Published '}
          <Link to={bookPath(saved.title)}>{saved.title}</Link>.
          {' '}{saved.edited ? 'They show up on the site once they\'ve' : 'It shows up on the site once it\'s'} been processed, in a few seconds.
        </p>
      )}
      {error && <p className="error">{error}</p>}
      {!books && !error && <p className="admin-form-hint">Loading...</p>}
      {books && books.length === 0 && <p className="admin-form-hint">No reviews yet. Start one with New Review.</p>}

      {books && books.length > 0 && (
        <>
          <input
            type="text"
            value={filter}
            onChange={e => setFilter(e.target.value)}
            placeholder="Filter by title or author"
          />
          {shown.length === 0 && <p className="admin-form-hint">No reviews match.</p>}
          <ul className="admin-draft-list">
            {shown.map(book => (
              <li key={book.title} className="admin-draft">
                <Link to={bookPath(book.title)} className="admin-draft-link">
                  <span className="admin-draft-title">{book.title}</span>
                  <span className="admin-form-hint">
                    {book.author}{book.date_reviewed && ` · Reviewed ${book.date_reviewed}`}
                  </span>
                </Link>
                <Link
                  className="admin-back-button admin-draft-action"
                  to={`/admin/books/${encodeURIComponent(book.title)}/edit`}
                >
                  Edit
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export default BookReviewList;
