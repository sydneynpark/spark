import React, { useState, useEffect } from 'react';
import ApiService from '../services/api';

const PhotoThumbnail = ({ s3Uri, species: speciesProp, family: familyProp, order: orderProp, onClick }) => {
  const [fetched, setFetched] = useState(null);

  useEffect(() => {
    if (!speciesProp && !familyProp && !orderProp) {
      ApiService.fetchPhoto(s3Uri)
        .then(photo => setFetched(photo))
        .catch(() => setFetched({}));
    }
  }, [s3Uri, speciesProp, familyProp, orderProp]);

  const species = speciesProp || fetched?.species;
  const family = familyProp || fetched?.family;
  const order = orderProp || fetched?.order;

  return (
    <div className="photo-item" onClick={onClick}>
      <div className="photo-thumbnail">
        <img
          src={ApiService.getThumbnailUrl(s3Uri)}
          alt={species || 'Bird photo'}
          onError={e => { e.target.src = '/images/placeholder.jpg'; }}
        />
      </div>
      {(species || family || order) && (
        <div className="photo-info">
          {species && <h4>{species}</h4>}
          {family && <p className="taxonomy-info">{family}</p>}
          {order && <p className="taxonomy-info">{order}</p>}
        </div>
      )}
    </div>
  );
};

export default PhotoThumbnail;
