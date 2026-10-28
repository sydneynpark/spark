import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import ApiService from '../services/api';
import PhotoDateTree, { TreeRow, buildDateHierarchy } from './PhotoDateTree';

const GALLERY_PATH = '/birds/gallery';

const Birds = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [hierarchy, setHierarchy] = useState({});
  const [dateHierarchy, setDateHierarchy] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const activeTab = searchParams.get('tab') === 'date' ? 'date' : 'taxonomy';
  const selectTab = (tab) => setSearchParams(tab === 'date' ? { tab: 'date' } : {});

  useEffect(() => {
    loadPhotos();
  }, []);

  const loadPhotos = async () => {
    try {
      setLoading(true);
      const [photoData, taxonomyData] = await Promise.all([
        ApiService.fetchBirds(),
        ApiService.fetchTaxonomy(),
      ]);
      setHierarchy(taxonomyData);
      setDateHierarchy(buildDateHierarchy(photoData));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const renderRow = (rank, name, count) => (
    <TreeRow galleryPath={GALLERY_PATH} type={rank} value={name} name={name} count={count} />
  );

  const renderSpeciesRow = (species, speciesData) => (
    <TreeRow
      galleryPath={GALLERY_PATH}
      type="species"
      value={species}
      name={species}
      count={speciesData.count}
      thumbnails={speciesData.thumbnails.map(uri => ({ s3_uri: uri }))}
    />
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
                          {renderSpeciesRow(species, speciesData)}
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
        <p>Loading photos...</p>
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

  const hasContent = activeTab === 'taxonomy'
    ? Object.keys(hierarchy).length > 0
    : Object.keys(dateHierarchy).length > 0;

  return (
    <div className="photos-page">
      <h2>Bird Photo Gallery</h2>

      <div className="photos-tabs">
        <span className="photos-tabs-label">Browse by...</span>
        <button
          type="button"
          className={`photos-tab${activeTab === 'taxonomy' ? ' active' : ''}`}
          onClick={() => selectTab('taxonomy')}
        >
          Taxonomy
        </button>
        <button
          type="button"
          className={`photos-tab${activeTab === 'date' ? ' active' : ''}`}
          onClick={() => selectTab('date')}
        >
          Date
        </button>
      </div>

      <div className="taxonomy-hierarchy">
        {hasContent ? (
          <div className="taxonomy-tree">
            {activeTab === 'taxonomy'
              ? renderHierarchy()
              : <PhotoDateTree hierarchy={dateHierarchy} galleryPath={GALLERY_PATH} />}
          </div>
        ) : (
          <p>No photos found.</p>
        )}
      </div>
    </div>
  );
};

export default Birds;
