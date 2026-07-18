import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import ApiService from '../services/api';
import {
  getPhotoDateParts,
  monthName,
  monthValue,
  dayValue,
  formatDayLabel,
} from '../utils/photoDate';

const ThumbnailStack = ({ photos }) => (
  <div className="thumb-stack">
    {photos.slice(0, 3).map(photo => (
      <img
        key={photo.s3_uri}
        className="thumb-stack-img"
        src={ApiService.getThumbnailUrl(photo.s3_uri)}
        alt=""
        onError={e => { e.target.src = '/images/placeholder-unknown.jpg'; }}
      />
    ))}
  </div>
);

const Photos = () => {
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
      const photoData = await ApiService.fetchPhotos();
      setHierarchy(buildHierarchy(photoData));
      setDateHierarchy(buildDateHierarchy(photoData));
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

  const buildDateHierarchy = (photoData) => {
    const hierarchy = {};

    photoData.forEach(photo => {
      const parts = getPhotoDateParts(photo);
      if (!parts) return;
      const { year, month, day } = parts;

      if (!hierarchy[year]) {
        hierarchy[year] = { count: 0, months: {} };
      }

      if (!hierarchy[year].months[month]) {
        hierarchy[year].months[month] = { count: 0, days: {} };
      }

      if (!hierarchy[year].months[month].days[day]) {
        hierarchy[year].months[month].days[day] = { count: 0, photos: [] };
      }

      hierarchy[year].count++;
      hierarchy[year].months[month].count++;
      hierarchy[year].months[month].days[day].count++;
      hierarchy[year].months[month].days[day].photos.push(photo);
    });

    return hierarchy;
  };

  const renderRow = (rank, name, count, value = name) => (
    <Link
      to={`/gallery?type=${rank}&value=${encodeURIComponent(value)}`}
      className={`taxonomy-row rank-${rank}`}
    >
      <span className="taxonomy-name">{name}</span>
      <span className="taxonomy-count">{count}</span>
    </Link>
  );

  const renderDayRow = (parts, dayData) => (
    <Link
      to={`/gallery?type=day&value=${encodeURIComponent(dayValue(parts))}`}
      className="taxonomy-row rank-day"
    >
      <ThumbnailStack photos={dayData.photos} />
      <span className="taxonomy-name">{formatDayLabel(parts)}</span>
      <span className="taxonomy-count">{dayData.count}</span>
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

  const renderDateHierarchy = () => {
    const years = Object.keys(dateHierarchy).sort((a, b) => b.localeCompare(a));

    return years.map(year => {
      const yearData = dateHierarchy[year];
      const months = Object.keys(yearData.months).sort((a, b) => b.localeCompare(a));

      return (
        <div key={year} className="taxonomy-node">
          {renderRow('year', year, yearData.count)}

          <div className="taxonomy-children">
            {months.map(month => {
              const monthData = yearData.months[month];
              const days = Object.keys(monthData.days).sort((a, b) => b.localeCompare(a));

              return (
                <div key={month} className="taxonomy-node">
                  {renderRow('month', monthName(month), monthData.count, monthValue({ year, month }))}

                  <div className="taxonomy-children">
                    {days.map(day => (
                      <div key={day} className="taxonomy-node">
                        {renderDayRow({ year, month, day }, monthData.days[day])}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      );
    });
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

      <p>{activeTab === 'taxonomy' ? 'Browse by taxonomic classification' : 'Browse by date captured'}</p>

      <div className="taxonomy-hierarchy">
        {hasContent ? (
          <div className="taxonomy-tree">
            {activeTab === 'taxonomy' ? renderHierarchy() : renderDateHierarchy()}
          </div>
        ) : (
          <p>No photos found.</p>
        )}
      </div>
    </div>
  );
};

export default Photos;
