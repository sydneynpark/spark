import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import ApiService from '../services/api';
import { usePageTitle } from '../utils/pageTitle';
import ThumbnailList, { ThumbnailListItem } from './ThumbnailList';
import SortBar from './SortBar';
import TagInput from './TagInput';
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
  // The tags the posts are filtered by, kept in the URL to link to (as
  // ?tag=A&tag=B): just the posts with all of them are shown.
  const [searchParams, setSearchParams] = useSearchParams();
  const allTags = useMemo(() => tagsInUse(posts).map(({ tag }) => tag), [posts]);
  // As spelled in the posts, whatever the URL's case.
  const filterTags = useMemo(() => searchParams.getAll('tag').map(
    tag => allTags.find(t => t.toLowerCase() === tag.toLowerCase()) || tag,
  ), [searchParams, allTags]);
  const shownPosts = useMemo(
    () => posts.filter(post => filterTags.every(tag => hasTag(post, tag))),
    [posts, filterTags],
  );
  // Only ones some shown post has, so adding one never leaves none shown.
  const tagSuggestions = useMemo(() => tagsInUse(shownPosts).map(({ tag }) => tag), [shownPosts]);
  const { sortedItems: sortedPosts, sortKey, sortDirection, handleSort } = useSort(shownPosts, 'date', 'desc');

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
          <div className="blog-controls">
            <SortBar options={SORT_OPTIONS} sortKey={sortKey} sortDirection={sortDirection} onSort={handleSort} />
            {allTags.length > 0 && (
              <div className="tag-filter">
                <span id="tag-filter-label" className="sort-bar-label">Tags:</span>
                <TagInput
                  tags={filterTags}
                  onChange={tags => setSearchParams({ tag: tags })}
                  suggestions={tagSuggestions}
                  allowNew={false}
                  labelledBy="tag-filter-label"
                  placeholder={filterTags.length ? '' : 'Filter by tag'}
                />
              </div>
            )}
          </div>
          {sortedPosts.length === 0 && <p>No posts have all of those tags.</p>}
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
