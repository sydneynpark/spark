import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import ApiService from '../services/api';

const PHOTO_BUCKET = 'spark.wiki.photos';

function formatDate(dateStr) {
  const [year, month, day] = dateStr.split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  });
}

function BlogPost() {
  const { postId } = useParams();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lightboxUri, setLightboxUri] = useState(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);

  const closeLightbox = useCallback(() => {
    setLightboxUri(null);
    setImageLoaded(false);
    setImageError(false);
  }, []);

  const openLightbox = useCallback((s3Uri) => {
    setLightboxUri(s3Uri);
    setImageLoaded(false);
    setImageError(false);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e) => { if (e.key === 'Escape') closeLightbox(); };
    if (lightboxUri) document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [lightboxUri, closeLightbox]);

  useEffect(() => {
    ApiService.fetchPost(postId)
      .then(setPost)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [postId]);

  const markdownComponents = {
    h1: ({ children }) => <h2>{children}</h2>,
    code: ({ children, className }) => {
      const text = String(children).trim();
      if (!className && text.startsWith('photo://')) {
        const s3Uri = `s3://${PHOTO_BUCKET}/${text.slice('photo://'.length)}`;
        return (
          <span className="blog-photo-embed" onClick={() => openLightbox(s3Uri)}>
            <img src={ApiService.getThumbnailUrl(s3Uri)} alt="Photo" />
          </span>
        );
      }
      return <code className={className}>{children}</code>;
    },
  };

  if (loading) return <div className="blog-post-page"><p>Loading...</p></div>;
  if (error) return <div className="blog-post-page"><p className="error">Error loading post: {error}</p></div>;
  if (!post) return null;

  return (
    <div className="blog-post-page">
      <Link to="/blog" className="back-link">← Back to Blog</Link>
      <article className="blog-post">
        <header className="post-header">
          <h1>{post.title}</h1>
          {post.date && <time className="post-date">{formatDate(post.date)}</time>}
        </header>
        <div className="post-content">
          <ReactMarkdown components={markdownComponents}>{post.content}</ReactMarkdown>
        </div>
      </article>

      {lightboxUri && (
        <div className="lightbox-overlay" onClick={closeLightbox}>
          <div className="lightbox-content" onClick={e => e.stopPropagation()}>
            <button className="lightbox-close" onClick={closeLightbox}>✕</button>
            {!imageLoaded && !imageError && <div className="lightbox-loading">Loading...</div>}
            {imageError && <div className="lightbox-error">Failed to load image</div>}
            <img
              src={ApiService.getFullsizeUrl(lightboxUri)}
              alt="Full size photo"
              className="lightbox-image"
              style={{ display: imageLoaded ? 'block' : 'none' }}
              onLoad={() => setImageLoaded(true)}
              onError={() => setImageError(true)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default BlogPost;
