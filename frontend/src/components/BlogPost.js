import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import ApiService from '../services/api';
import { usePageTitle } from '../utils/pageTitle';
import PostContent, { PostDates } from './PostContent';

function BlogPost() {
  const { slug } = useParams();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    ApiService.fetchPost(slug)
      .then(setPost)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [slug]);

  usePageTitle(post?.title || 'Blog');

  if (loading) return <div className="blog-post-page"><p>Loading...</p></div>;
  if (error) return <div className="blog-post-page"><p className="error">Error loading post: {error}</p></div>;
  if (!post) return null;

  return (
    <div className="blog-post-page">
      <Link to="/blog" className="back-link">← Back to Blog</Link>
      <article className="blog-post">
        <header className="post-header">
          <h1>{post.title}</h1>
          <PostDates date={post.date} written={post.written} />
        </header>
        <PostContent content={post.content} />
      </article>
    </div>
  );
}

export default BlogPost;
