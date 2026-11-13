import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import ApiService from '../../services/api';
import { usePageTitle } from '../../utils/pageTitle';

// The public /books endpoint only returns its first 50 by default.
const BOOK_LIMIT = 1000;

// Picks which review to edit, from the same list the public Books page shows
// (most recently reviewed first).
function BookReviewList() {
  usePageTitle('Edit Book Review');
  const [books, setBooks] = useState(null);
  const [filter, setFilter] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    ApiService.fetchBooks(BOOK_LIMIT)
      .then(setBooks)
      .catch(err => setError(err.message));
  }, []);

  const query = filter.trim().toLowerCase();
  const shown = (books || []).filter(book =>
    !query || book.title.toLowerCase().includes(query) || (book.author || '').toLowerCase().includes(query));

  return (
    <div className="admin-page admin-book-list-page">
      <Link to="/admin" className="back-link">← Back to Admin</Link>
      <h2>Edit Book Review</h2>

      {error && <p className="error">{error}</p>}
      {!books && !error && <p>Loading reviews...</p>}

      {books && (
        <>
          <input
            type="text"
            value={filter}
            onChange={e => setFilter(e.target.value)}
            placeholder="Filter by title or author"
          />
          {shown.length === 0 && <p className="admin-form-hint">No reviews match.</p>}
          <ul className="admin-book-list">
            {shown.map(book => (
              <li key={book.title}>
                <Link to={`/admin/books/${encodeURIComponent(book.title)}/edit`}>
                  <span className="admin-book-list-title">{book.title}</span>
                  <span className="admin-book-list-meta">
                    {book.author}{book.date_reviewed && ` · ${book.date_reviewed}`}
                  </span>
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
