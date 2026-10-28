import React, { useState, useEffect } from 'react';
import ApiService from '../services/api';
import StarRating from './StarRating';
import SortBar from './SortBar';
import ReadingShelf from './ReadingShelf';
import ThumbnailList, { ThumbnailListItem } from './ThumbnailList';
import { useSort } from '../utils/sort';
import { usePageTitle } from '../utils/pageTitle';

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

  usePageTitle('Books');

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
          <ThumbnailList>
            {sortedBooks.map(book => (
              <ThumbnailListItem
                key={book.title}
                to={`/books/${encodeURIComponent(book.title)}`}
                src={ApiService.getBookCoverUrl(book.cover_key)}
                placeholderSrc="/images/placeholder-book.jpg"
                alt={`Cover of ${book.title}`}
                shape="portrait"
              >
                <h3>{book.title}</h3>
                {book.author && <p className="book-author">by {book.author}</p>}
                {book.date_reviewed && <time>{formatDate(book.date_reviewed)}</time>}
                <StarRating rating={book.star_rating} />
              </ThumbnailListItem>
            ))}
          </ThumbnailList>
        </>
      )}
    </div>
  );
}

export default Books;
