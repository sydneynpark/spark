import React, { useState, useEffect } from 'react';
import ApiService from '../services/api';
import PhotoDateTree, { buildDateHierarchy } from './PhotoDateTree';
import { usePageTitle } from '../utils/pageTitle';

// Photos that aren't of birds, browsed by the day they were taken, as the
// bird photos are on their Date tab.
const Photos = () => {
  const [dateHierarchy, setDateHierarchy] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  usePageTitle('Photos');

  useEffect(() => {
    loadPhotos();
  }, []);

  const loadPhotos = async () => {
    try {
      setLoading(true);
      setError(null);
      setDateHierarchy(buildDateHierarchy(await ApiService.fetchPhotos()));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="photos-page">
        <h2>Photos</h2>
        <p>Loading photos...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="photos-page">
        <h2>Photos</h2>
        <p className="error">Error loading photos: {error}</p>
        <button onClick={loadPhotos}>Retry</button>
      </div>
    );
  }

  return (
    <div className="photos-page">
      <h2>Photos</h2>

      <div className="taxonomy-hierarchy">
        {Object.keys(dateHierarchy).length > 0 ? (
          <div className="taxonomy-tree">
            <PhotoDateTree hierarchy={dateHierarchy} galleryPath="/photos/gallery" />
          </div>
        ) : (
          <p>No photos found.</p>
        )}
      </div>
    </div>
  );
};

export default Photos;
