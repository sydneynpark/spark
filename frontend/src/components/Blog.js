import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import ApiService from '../services/api';
import { usePageTitle } from '../utils/pageTitle';
import ThumbnailList, { ThumbnailListItem } from './ThumbnailList';
import SortBar from './SortBar';
import { useSort } from '../utils/sort';
import { hasTag, tagsInUse } from '../utils/postTags';

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
  // The tag the posts are filtered by, if any, kept in the URL to link to.
  const [searchParams, setSearchParams] = useSearchParams();
  const tag = searchParams.get('tag');
  const tags = useMemo(() => tagsInUse(posts), [posts]);
  const shownPosts = useMemo(() => (tag ? posts.filter(post => hasTag(post, tag)) : posts), [posts, tag]);
  const { sortedItems: sortedPosts, sortKey, sortDirection, handleSort } = useSort(shownPosts, 'date', 'desc');

  function filterBy(newTag) {
    setSearchParams(newTag ? { tag: newTag } : {});
  }

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
          {tags.length > 0 && (
            <div className="sort-bar tag-filter">
              <span className="sort-bar-label">Tags:</span>
              {tags.map(({ tag: name, count }) => {
                const active = tag !== null && name.toLowerCase() === tag.toLowerCase();
                return (
                  <button
                    key={name}
                    type="button"
                    className={`sort-bar-button${active ? ' sort-bar-button--active' : ''}`}
                    onClick={() => filterBy(active ? null : name)}
                    aria-pressed={active}
                  >
                    {name} <span className="tag-filter-count">{count}</span>
                  </button>
                );
              })}
              {tag && (
                <button type="button" className="tag-filter-clear" onClick={() => filterBy(null)}>
                  Show all posts
                </button>
              )}
            </div>
          )}
          <SortBar options={SORT_OPTIONS} sortKey={sortKey} sortDirection={sortDirection} onSort={handleSort} />
          {sortedPosts.length === 0 && <p>No posts are tagged "{tag}".</p>}
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
                {post.tags?.length > 0 && (
                  <ul className="post-tags">
                    {post.tags.map(name => <li key={name} className="tag-chip">{name}</li>)}
                  </ul>
                )}
              </ThumbnailListItem>
            ))}
          </ThumbnailList>
        </>
      )}
    </div>
  );
}

export default Blog;
