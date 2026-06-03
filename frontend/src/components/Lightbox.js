import { useState, useEffect } from 'react';

function Lightbox({ src, alt, caption, onClose }) {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    setImageLoaded(false);
    setImageError(false);
  }, [src]);

  useEffect(() => {
    if (!src) return;
    const handleKeyDown = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [src, onClose]);

  if (!src) return null;

  return (
    <div className="lightbox-overlay" onClick={onClose}>
      <div className="lightbox-content" onClick={e => e.stopPropagation()}>
        <button className="lightbox-close" onClick={onClose}>✕</button>
        {!imageLoaded && !imageError && <div className="lightbox-loading">Loading...</div>}
        {imageError && <div className="lightbox-error">Failed to load image</div>}
        <img
          src={src}
          alt={alt}
          className="lightbox-image"
          style={{ display: imageLoaded ? 'block' : 'none' }}
          onLoad={() => setImageLoaded(true)}
          onError={() => setImageError(true)}
        />
        {caption && (
          <div className="lightbox-caption">
            <h3>{caption.species || 'Unknown Species'}</h3>
            {caption.family && <p>{caption.family}</p>}
            {caption.order && <p>{caption.order}</p>}
          </div>
        )}
      </div>
    </div>
  );
}

export default Lightbox;
