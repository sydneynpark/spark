import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import ApiService from '../services/api';

function BlogPost() {
  const { postId } = useParams();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    ApiService.fetchPost(postId)
      .then(setPost)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [postId]);

  if (loading) return <div className="blog-post-page"><p>Loading...</p></div>;
  if (error) return <div className="blog-post-page"><p className="error">Error loading post: {error}</p></div>;
  if (!post) return null;

  return (
    <div className="blog-post-page">
      <Link to="/blog" className="back-link">← Back to Blog</Link>
      <article className="blog-post">
        <header className="post-header">
          <h1>{post.title}</h1>
          {post.date && <time className="post-date">{post.date}</time>}
        </header>
        <div className="post-content">
          <ReactMarkdown>{post.content}</ReactMarkdown>
        </div>
      </article>
    </div>
  );
}

export default BlogPost;
