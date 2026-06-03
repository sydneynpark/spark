import React, { useState, useEffect } from 'react';
import ApiService from '../services/api';
import PostCard from './PostCard';

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
        <ul className="post-list">
          {posts.map(post => (
            <PostCard key={post.id} post={post} />
          ))}
        </ul>
      )}
    </div>
  );
}

export default Blog;
