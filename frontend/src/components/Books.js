import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import ApiService from '../services/api';
import StarRating from './StarRating';
import SortBar from './SortBar';
import ReadingShelf from './ReadingShelf';
import { useSort } from '../utils/sort';

function formatDate(dateStr) {
  const [year, month, day] = dateStr.split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  });
}

const SORT_OPTIONS = [
  { key: 'date_reviewed', label: 'Date Read', defaultDirection: 'desc' },
  { key: 'title', label: 'Title', defaultDirection: 'asc' },
  { key: 'author', label: 'Author', defaultDirection: 'asc' },
  { key: 'star_rating', label: 'Rating', defaultDirection: 'desc' },
];

function Books() {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { sortedItems: sortedBooks, sortKey, sortDirection, handleSort } = useSort(books, 'date_reviewed', 'desc');

  useEffect(() => {
    ApiService.fetchBooks()
      .then(setBooks)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="books-page"><p>Loading book reviews...</p></div>;
  if (error) return <div className="books-page"><p className="error">Error loading book reviews: {error}</p></div>;

  return (
    <div className="books-page">
      <h2>Book Reviews</h2>
      {books.length === 0 ? (
        <p>No book reviews yet.</p>
      ) : (
        <>
          <ReadingShelf books={books} />
          <SortBar options={SORT_OPTIONS} sortKey={sortKey} sortDirection={sortDirection} onSort={handleSort} />
          <ul className="book-list">
            {sortedBooks.map(book => (
              <li key={book.title} className="book-item">
                <Link to={`/books/${encodeURIComponent(book.title)}`}>
                  <img
                    className={`book-cover-thumb${book.cover_key ? '' : ' book-cover-thumb--placeholder'}`}
                    src={book.cover_key ? ApiService.getBookCoverUrl(book.cover_key) : '/images/placeholder-book.jpg'}
                    alt={`Cover of ${book.title}`}
                    loading="lazy"
                    onError={e => { e.target.src = '/images/placeholder-book.jpg'; e.target.classList.add('book-cover-thumb--placeholder'); }}
                  />
                  <div className="book-item-text">
                    <h3>{book.title}</h3>
                    {book.author && <p className="book-author">by {book.author}</p>}
                    {book.date_reviewed && <time>{formatDate(book.date_reviewed)}</time>}
                    <StarRating rating={book.star_rating} />
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export default Books;
