import React, { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import ApiService from '../services/api';
import PhotoThumbnail from './PhotoThumbnail';
import Lightbox from './Lightbox';

const LABEL_BY_TYPE = { species: 'Species', family: 'Family', order: 'Order', class: 'Class' };

const Gallery = () => {
  const [searchParams] = useSearchParams();
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const type = searchParams.get('type');
  const value = searchParams.get('value');

  useEffect(() => {
    loadPhotos();
  }, [type, value]);

  const closeLightbox = useCallback(() => setSelectedPhoto(null), []);
  const openLightbox = (photo) => setSelectedPhoto(photo);

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
    return `${LABEL_BY_TYPE[type] || type}: ${value}`;
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
            <PhotoThumbnail
              key={`${photo.s3_uri}-${idx}`}
              s3Uri={photo.s3_uri}
              species={photo.species}
              family={photo.family}
              order={photo.order}
              onClick={() => openLightbox(photo)}
            />
          ))}
        </div>
      ) : (
        <div className="no-photos">
          <p>No photos found for this filter.</p>
          <Link to="/photos">Browse all categories</Link>
        </div>
      )}

      <Lightbox
        src={selectedPhoto ? ApiService.getFullsizeUrl(selectedPhoto.s3_uri) : null}
        alt={selectedPhoto?.species || 'Bird photo'}
        caption={selectedPhoto}
        onClose={closeLightbox}
      />
    </div>
  );
};

export default Gallery;
