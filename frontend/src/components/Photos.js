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

  const renderRow = (rank, name, count) => (
    <Link
      to={`/gallery?type=${rank}&value=${encodeURIComponent(name)}`}
      className={`taxonomy-row rank-${rank}`}
    >
      <span className="taxonomy-name">{name}</span>
      <span className="taxonomy-count">{count}</span>
    </Link>
  );

  const renderHierarchy = () => {
    return Object.entries(hierarchy).map(([className, classData]) => (
      <div key={className} className="taxonomy-node">
        {renderRow('class', className, classData.count)}

        <div className="taxonomy-children">
          {Object.entries(classData.orders).map(([order, orderData]) => (
            <div key={order} className="taxonomy-node">
              {renderRow('order', order, orderData.count)}

              <div className="taxonomy-children">
                {Object.entries(orderData.families).map(([family, familyData]) => (
                  <div key={family} className="taxonomy-node">
                    {renderRow('family', family, familyData.count)}

                    <div className="taxonomy-children">
                      {Object.entries(familyData.species).map(([species, speciesData]) => (
                        <div key={species} className="taxonomy-node">
                          {renderRow('species', species, speciesData.count)}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
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
          <div className="taxonomy-tree">{renderHierarchy()}</div>
        ) : (
          <p>No photos found.</p>
        )}
      </div>
    </div>
  );
};

export default Photos;