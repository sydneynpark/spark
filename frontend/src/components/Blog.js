import React, { useState, useEffect } from 'react';
import ApiService from '../services/api';
import { usePageTitle } from '../utils/pageTitle';
import ThumbnailList, { ThumbnailListItem } from './ThumbnailList';
import SortBar from './SortBar';
import { useSort } from '../utils/sort';

// A post's `date` is the one it's shown under, and `written` when it was
// written: the same, unless it was written later about something past.
const SORT_OPTIONS = [
  { key: 'date', label: 'Date', defaultDirection: 'desc' },
  { key: 'written', label: 'Date Written', defaultDirection: 'desc' },
];

function Blog() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { sortedItems: sortedPosts, sortKey, sortDirection, handleSort } = useSort(posts, 'date', 'desc');

  usePageTitle('Blog');

  useEffect(() => {
    ApiService.fetchPosts()
      .then(setPosts)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="blog-page"><p>Loading posts...</p></div>;
  if (error) return <div className="blog-page"><p className="error">Error loading posts: {error}</p></div>;

  return (
    <div className="blog-page">
      <h2>Blog</h2>
      {posts.length === 0 ? (
        <p>No posts yet.</p>
      ) : (
        <>
          <SortBar options={SORT_OPTIONS} sortKey={sortKey} sortDirection={sortDirection} onSort={handleSort} />
          <ThumbnailList>
            {sortedPosts.map(post => (
              <ThumbnailListItem
                key={post.key}
                to={`/blog/${encodeURIComponent(post.slug)}`}
                src={post.photo && ApiService.getThumbnailUrl(post.photo)}
                placeholderSrc="/images/placeholder-blogpost.jpg"
                alt=""
              >
                <h3>{post.title}</h3>
                {post.date && (
                  <p className="post-list-dates">
                    <time dateTime={post.date}>{post.date}</time>
                    {post.written && post.written !== post.date && (
                      <> · Written <time dateTime={post.written}>{post.written}</time></>
                    )}
                  </p>
                )}
                {post.preview && <p className="post-preview">{post.preview}</p>}
              </ThumbnailListItem>
            ))}
          </ThumbnailList>
        </>
      )}
    </div>
  );
}

export default Blog;
