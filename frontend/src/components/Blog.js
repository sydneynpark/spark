import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import ApiService from '../services/api';

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
            <li key={post.id} className="post-item">
              <Link to={`/blog/${post.id}`}>
                <h3>{post.title}</h3>
                {post.date && <time>{post.date}</time>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default Blog;
