import React, { useState, useEffect } from 'react';
import ApiService from '../services/api';
import ThumbnailList, { ThumbnailListItem } from './ThumbnailList';

function Blog() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
        <ThumbnailList>
          {posts.map(post => (
            <ThumbnailListItem
              key={post.key}
              to={`/blog/${encodeURIComponent(post.slug)}`}
              src={post.photo && ApiService.getThumbnailUrl(post.photo)}
              placeholderSrc="/images/placeholder-blogpost.jpg"
              alt=""
            >
              <h3>{post.title}</h3>
              {post.date && <time>{post.date}</time>}
              {post.preview && <p className="post-preview">{post.preview}</p>}
            </ThumbnailListItem>
          ))}
        </ThumbnailList>
      )}
    </div>
  );
}

export default Blog;
