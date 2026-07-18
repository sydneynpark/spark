import React, { useState, useEffect, useCallback } from 'react';
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
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const type = searchParams.get('type');
  const value = searchParams.get('value');

  useEffect(() => {
    loadPhotos();
  }, [type, value]);

  const closeLightbox = useCallback(() => {
    setSelectedPhoto(null);
    setImageLoaded(false);
    setImageError(false);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e) => { if (e.key === 'Escape') closeLightbox(); };
    if (selectedPhoto) document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedPhoto, closeLightbox]);

  const openLightbox = (photo) => {
    setSelectedPhoto(photo);
    setImageLoaded(false);
    setImageError(false);
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
              onClick={() => openLightbox(photo)}
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
          <div className="lightbox-content" onClick={e => e.stopPropagation()}>
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
              <h3>{selectedPhoto.species || 'Unknown Species'}</h3>
              {selectedPhoto.family && <p>{selectedPhoto.family}</p>}
              {selectedPhoto.order && <p>{selectedPhoto.order}</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Gallery;
