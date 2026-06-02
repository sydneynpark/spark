import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import ApiService from '../services/api';

const Photos = () => {
  const [photos, setPhotos] = useState([]);
  const [hierarchy, setHierarchy] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadPhotos();
  }, []);

  const loadPhotos = async () => {
    try {
      setLoading(true);
      const photoData = await ApiService.fetchPhotos();
      setPhotos(photoData);
      setHierarchy(buildHierarchy(photoData));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const buildHierarchy = (photoData) => {
    const hierarchy = {};

    photoData.forEach(photo => {
      const className = photo.class || 'Unknown Class';
      const order = photo.order || 'Unknown Order';
      const family = photo.family || 'Unknown Family';
      const species = photo.species || 'Unknown Species';

      // Build nested structure
      if (!hierarchy[className]) {
        hierarchy[className] = { count: 0, orders: {} };
      }
      
      if (!hierarchy[className].orders[order]) {
        hierarchy[className].orders[order] = { count: 0, families: {} };
      }
      
      if (!hierarchy[className].orders[order].families[family]) {
        hierarchy[className].orders[order].families[family] = { count: 0, species: {} };
      }
      
      if (!hierarchy[className].orders[order].families[family].species[species]) {
        hierarchy[className].orders[order].families[family].species[species] = { count: 0 };
      }

      // Increment counts
      hierarchy[className].count++;
      hierarchy[className].orders[order].count++;
      hierarchy[className].orders[order].families[family].count++;
      hierarchy[className].orders[order].families[family].species[species].count++;
    });

    return hierarchy;
  };

  const renderHierarchy = () => {
    return Object.entries(hierarchy).map(([className, classData]) => (
      <div key={className} className="taxonomy-class">
        <Link to={`/gallery?type=class&value=${encodeURIComponent(className)}`} className="taxonomy-item level-0">
          <strong>{className}</strong> <span className="count">({classData.count} photos)</span>
        </Link>

        {Object.entries(classData.orders).map(([order, orderData]) => (
          <div key={order} className="taxonomy-order">
            <Link to={`/gallery?type=order&value=${encodeURIComponent(order)}`} className="taxonomy-item level-1">
              {order} <span className="count">({orderData.count} photos)</span>
            </Link>

            {Object.entries(orderData.families).map(([family, familyData]) => (
              <div key={family} className="taxonomy-family">
                <Link to={`/gallery?type=family&value=${encodeURIComponent(family)}`} className="taxonomy-item level-2">
                  {family} <span className="count">({familyData.count} photos)</span>
                </Link>

                {Object.entries(familyData.species).map(([species, speciesData]) => (
                  <div key={species} className="taxonomy-species">
                    <Link to={`/gallery?type=species&value=${encodeURIComponent(species)}`} className="taxonomy-item level-3">
                      <em>{species}</em> <span className="count">({speciesData.count} photos)</span>
                    </Link>
                  </div>
                ))}
              </div>
            ))}
          </div>
        ))}
      </div>
    ));
  };

  if (loading) {
    return (
      <div className="photos-page">
        <h2>Bird Photo Gallery</h2>
        <p>Loading taxonomic hierarchy...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="photos-page">
        <h2>Bird Photo Gallery</h2>
        <p className="error">Error loading photos: {error}</p>
        <button onClick={loadPhotos}>Retry</button>
      </div>
    );
  }

  return (
    <div className="photos-page">
      <h2>Bird Photo Gallery</h2>
      <p>Browse by taxonomic classification</p>
      
      <div className="taxonomy-hierarchy">
        {Object.keys(hierarchy).length > 0 ? (
          renderHierarchy()
        ) : (
          <p>No photos found.</p>
        )}
      </div>
    </div>
  );
};

export default Photos;