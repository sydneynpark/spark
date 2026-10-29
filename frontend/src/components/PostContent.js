import { useState, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import ApiService from '../services/api';

// photo://<key> embeds name a photo by its key in this bucket, e.g.
// photo://birds/2026/05/23/<photo>.jpg or photo://photos/2026/07/04/<photo>.jpg.
const PHOTOS_BUCKET = 'spark.wiki.photos';

// 'YYYY-MM-DD', as a post's date reads at the top of it.
export function formatPostDate(dateStr) {
  const [year, month, day] = dateStr.split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  });
}

// A post's body: its markdown, with each photo:// embed shown as a tile of the
// photo's thumbnail, which opens it full size. photoUrls gives a URL to show instead,
// by key, for photos the CDN doesn't serve -- a draft's, until it's published.
function PostContent({ content, photoUrls = {} }) {
  const [lightboxSrc, setLightboxSrc] = useState(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);

  const closeLightbox = useCallback(() => {
    setLightboxSrc(null);
    setImageLoaded(false);
    setImageError(false);
  }, []);

  const openLightbox = useCallback((src) => {
    setLightboxSrc(src);
    setImageLoaded(false);
    setImageError(false);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e) => { if (e.key === 'Escape') closeLightbox(); };
    if (lightboxSrc) document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [lightboxSrc, closeLightbox]);

  const markdownComponents = {
    h1: ({ children }) => <h2>{children}</h2>,
    code: ({ children, className }) => {
      const text = String(children).trim();
      if (!className && text.startsWith('photo://')) {
        const key = text.slice('photo://'.length);
        const s3Uri = `s3://${PHOTOS_BUCKET}/${key}`;
        const url = photoUrls[key];
        return (
          <span className="blog-photo-embed" onClick={() => openLightbox(url || ApiService.getFullsizeUrl(s3Uri))}>
            <img src={url || ApiService.getThumbnailUrl(s3Uri)} alt="Photo" />
          </span>
        );
      }
      return <code className={className}>{children}</code>;
    },
  };

  return (
    <>
      <div className="post-content">
        <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>
      </div>

      {lightboxSrc && (
        <div className="lightbox-overlay" onClick={closeLightbox}>
          <div className="lightbox-content" onClick={e => e.stopPropagation()}>
            <button className="lightbox-close" onClick={closeLightbox}>✕</button>
            {!imageLoaded && !imageError && <div className="lightbox-loading">Loading...</div>}
            {imageError && <div className="lightbox-error">Failed to load image</div>}
            <img
              src={lightboxSrc}
              alt="Full size photo"
              className="lightbox-image"
              style={{ display: imageLoaded ? 'block' : 'none' }}
              onLoad={() => setImageLoaded(true)}
              onError={() => setImageError(true)}
            />
          </div>
        </div>
      )}
    </>
  );
}

export default PostContent;
