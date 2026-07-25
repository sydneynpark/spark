import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import ApiService from '../services/api';
import RatingChart from './RatingChart';
import CommentaryTimeline from './CommentaryTimeline';

function formatDate(dateStr) {
  const [year, month, day] = dateStr.split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  });
}

function BookReview() {
  const { title } = useParams();
  const [book, setBook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    ApiService.fetchBook(title)
      .then(setBook)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [title]);

  if (loading) return <div className="book-review-page"><p>Loading...</p></div>;
  if (error) return <div className="book-review-page"><p className="error">Error loading book review: {error}</p></div>;
  if (!book) return null;

  return (
    <div className="book-review-page">
      <Link to="/books" className="back-link">← Back to Book Reviews</Link>
      <article className="book-review">
        <header className="book-review-header">
          <div className="book-review-header-content">
            <img
              className={`book-review-cover${book.cover_key ? '' : ' book-review-cover--placeholder'}`}
              src={book.cover_key ? ApiService.getBookCoverUrl(book.cover_key) : '/images/placeholder-book.jpg'}
              alt={`Cover of ${book.title}`}
              onError={e => { e.target.src = '/images/placeholder-book.jpg'; e.target.classList.add('book-review-cover--placeholder'); }}
            />
            <div className="book-review-header-text">
              <h1>{book.title}</h1>
              {book.author && <p className="book-review-author">by {book.author}</p>}
              {book.date_reviewed && <time className="book-review-date">{formatDate(book.date_reviewed)}</time>}
            </div>
          </div>
        </header>

        <div className="book-review-body">
          {book.rating_elements.length > 0 && (
            <section className="book-review-section">
              <h2>Rating</h2>
              <RatingChart ratingElements={book.rating_elements} />
            </section>
          )}

          {book.commentary.length > 0 && (
            <section className="book-review-section">
              <h2>Commentary</h2>
              <CommentaryTimeline commentary={book.commentary} />
            </section>
          )}
        </div>
      </article>
    </div>
  );
}

export default BookReview;
