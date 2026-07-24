import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import ApiService from '../services/api';
import { DATE_FILTER_TYPES, formatDateFilterLabel } from '../utils/photoDate';

const LABEL_BY_TYPE = {
  species: 'Species', family: 'Family', order: 'Order', class: 'Class',
  year: 'Year', month: 'Month', day: 'Day',
};

const Gallery = () => {
  const [searchParams] = useSearchParams();
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const touchStartRef = useRef(null);
  const type = searchParams.get('type');
  const value = searchParams.get('value');
  const selectedPhoto = selectedIndex !== null ? photos[selectedIndex] : null;

  useEffect(() => {
    loadPhotos();
  }, [type, value]);

  // Reset image load state whenever the lightbox opens or navigates to a
  // different photo.
  useEffect(() => {
    setImageLoaded(false);
    setImageError(false);
  }, [selectedIndex]);

  // Closing goes through history.back() so that the back entry pushed by
  // openLightbox is consumed here too, rather than by the underlying page.
  const closeLightbox = useCallback(() => {
    window.history.back();
  }, []);

  const showPrev = useCallback(() => {
    setSelectedIndex(i => (i === null || i <= 0) ? i : i - 1);
  }, []);

  const showNext = useCallback(() => {
    setSelectedIndex(i => (i === null || i >= photos.length - 1) ? i : i + 1);
  }, [photos.length]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') closeLightbox();
      else if (e.key === 'ArrowLeft') showPrev();
      else if (e.key === 'ArrowRight') showNext();
    };
    if (selectedPhoto) document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedPhoto, closeLightbox, showPrev, showNext]);

  // A back gesture/button press while the lightbox is open should close the
  // lightbox instead of navigating to the previous page.
  useEffect(() => {
    const handlePopState = () => {
      setSelectedIndex(null);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const openLightbox = (idx) => {
    window.history.pushState({ lightbox: true }, '');
    setSelectedIndex(idx);
  };

  const SWIPE_THRESHOLD = 50;

  const handleTouchStart = (e) => {
    const touch = e.touches[0];
    touchStartRef.current = { x: touch.clientX, y: touch.clientY };
  };

  const handleTouchEnd = (e) => {
    const start = touchStartRef.current;
    touchStartRef.current = null;
    if (!start) return;
    const touch = e.changedTouches[0];
    const dx = touch.clientX - start.x;
    const dy = touch.clientY - start.y;
    if (Math.abs(dx) > SWIPE_THRESHOLD && Math.abs(dx) > Math.abs(dy)) {
      if (dx < 0) showNext();
      else showPrev();
    }
  };

  const loadPhotos = async () => {
    try {
      setLoading(true);
      setError(null);
      const filter = {};
      if (type && value) {
        filter[type] = value;
      }
      const data = await ApiService.fetchPhotos(filter);
      setPhotos(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const filterLabel = () => {
    if (!type || !value) return 'All Photos';
    const displayValue = DATE_FILTER_TYPES.includes(type) ? formatDateFilterLabel(type, value) : value;
    return `${LABEL_BY_TYPE[type] || type}: ${displayValue}`;
  };

  const header = (
    <div className="gallery-header">
      <Link to="/photos" className="back-link">← Back to Browse</Link>
      <h2>Photo Gallery</h2>
    </div>
  );

  if (loading) {
    return (
      <div className="gallery-page">
        {header}
        <p>Loading photos...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="gallery-page">
        {header}
        <p className="error">Error loading photos: {error}</p>
        <button onClick={loadPhotos}>Retry</button>
      </div>
    );
  }

  return (
    <div className="gallery-page">
      <div className="gallery-header">
        <Link to="/photos" className="back-link">← Back to Browse</Link>
        <h2>Photo Gallery</h2>
        <p className="filter-info">{filterLabel()} ({photos.length} photos)</p>
      </div>
      {photos.length > 0 ? (
        <div className="photo-grid">
          {photos.map((photo, idx) => (
            <div
              className="photo-item"
              key={`${photo.s3_uri}-${idx}`}
              onClick={() => openLightbox(idx)}
            >
              <div className="photo-thumbnail">
                <img
                  src={ApiService.getThumbnailUrl(photo.s3_uri)}
                  alt={photo.species || 'Bird photo'}
                  onError={e => { e.target.src = '/images/placeholder-unknown.jpg'; }}
                />
              </div>
              <div className="photo-info">
                <h4>{photo.species || 'Unknown Species'}</h4>
                {photo.family && <p className="taxonomy-info">{photo.family}</p>}
                {photo.order && <p className="taxonomy-info">{photo.order}</p>}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="no-photos">
          <p>No photos found for this filter.</p>
          <Link to="/photos">Browse all categories</Link>
        </div>
      )}

      {selectedPhoto && (
        <div className="lightbox-overlay" onClick={closeLightbox}>
          {selectedIndex > 0 && (
            <button
              className="lightbox-nav lightbox-prev"
              onClick={e => { e.stopPropagation(); showPrev(); }}
              aria-label="Previous photo"
            >
              ‹
            </button>
          )}
          <div
            className="lightbox-content"
            onClick={e => e.stopPropagation()}
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
          >
            <button className="lightbox-close" onClick={closeLightbox}>✕</button>
            {!imageLoaded && !imageError && <div className="lightbox-loading">Loading...</div>}
            {imageError && <div className="lightbox-error">Failed to load image</div>}
            <img
              src={ApiService.getFullsizeUrl(selectedPhoto.s3_uri)}
              alt={selectedPhoto.species || 'Bird photo'}
              className="lightbox-image"
              style={{ display: imageLoaded ? 'block' : 'none' }}
              onLoad={() => setImageLoaded(true)}
              onError={() => setImageError(true)}
            />
            <div className="lightbox-caption">
              <div className="lightbox-caption-info">
                <h3>{selectedPhoto.species || 'Unknown Species'}</h3>
                {selectedPhoto.family && <p>{selectedPhoto.family}</p>}
                {selectedPhoto.order && <p>{selectedPhoto.order}</p>}
              </div>
              <a
                className="lightbox-open-new-tab"
                href={ApiService.getFullsizeUrl(selectedPhoto.s3_uri)}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Open full-res photo in new tab"
                title="Open in new tab"
              >
                <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
                  <path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z" />
                </svg>
              </a>
            </div>
          </div>
          {selectedIndex < photos.length - 1 && (
            <button
              className="lightbox-nav lightbox-next"
              onClick={e => { e.stopPropagation(); showNext(); }}
              aria-label="Next photo"
            >
              ›
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default Gallery;
