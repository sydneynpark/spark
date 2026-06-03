import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import ApiService from '../services/api';
import PhotoThumbnail from './PhotoThumbnail';
import Lightbox from './Lightbox';

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

  const closeLightbox = useCallback(() => setLightboxUri(null), []);
  const openLightbox = useCallback((s3Uri) => setLightboxUri(s3Uri), []);

  useEffect(() => {
    ApiService.fetchPost(postId)
      .then(setPost)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [postId]);

  const markdownComponents = {
    h1: ({ children }) => <h2>{children}</h2>,
    p: ({ children }) => {
      const arr = React.Children.toArray(children);
      if (arr.length === 1 && arr[0]?.type === PhotoThumbnail) {
        return <>{children}</>;
      }
      return <p>{children}</p>;
    },
    code: ({ children, className }) => {
      const text = String(children).trim();
      if (!className && text.startsWith('photo://')) {
        const s3Uri = `s3://${PHOTO_BUCKET}/${text.slice('photo://'.length)}`;
        return <PhotoThumbnail s3Uri={s3Uri} onClick={() => openLightbox(s3Uri)} />;
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

      <Lightbox
        src={lightboxUri ? ApiService.getFullsizeUrl(lightboxUri) : null}
        alt="Full size photo"
        onClose={closeLightbox}
      />
    </div>
  );
}

export default BlogPost;
