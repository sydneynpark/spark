import React from 'react';
import { Link } from 'react-router-dom';
import ApiService from '../services/api';
import {
  getPhotoDateParts,
  monthName,
  monthValue,
  dayValue,
  formatDayLabel,
} from '../utils/photoDate';

export const ThumbnailStack = ({ photos }) => (
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

// One row of a browse tree, linking to the gallery of its photos: those
// whose `type` (a taxonomic rank, or year, month, or day) is `value`.
export const TreeRow = ({ galleryPath, type, value, name, count, thumbnails }) => (
  <Link
    to={`${galleryPath}?type=${type}&value=${encodeURIComponent(value)}`}
    className={`taxonomy-row rank-${type}`}
  >
    {thumbnails && <ThumbnailStack photos={thumbnails} />}
    <span className="taxonomy-name">{name}</span>
    <span className="taxonomy-count">{count}</span>
  </Link>
);

// Photos grouped by the year, month, and day they were taken, for
// PhotoDateTree. Photos with no date are left out.
export function buildDateHierarchy(photoData) {
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
}

// Years, then months, then days, newest first, each linking to its photos
// in the gallery at galleryPath.
const PhotoDateTree = ({ hierarchy, galleryPath }) => {
  const years = Object.keys(hierarchy).sort((a, b) => b.localeCompare(a));

  return years.map(year => {
    const yearData = hierarchy[year];
    const months = Object.keys(yearData.months).sort((a, b) => b.localeCompare(a));

    return (
      <div key={year} className="taxonomy-node">
        <TreeRow galleryPath={galleryPath} type="year" value={year} name={year} count={yearData.count} />

        <div className="taxonomy-children">
          {months.map(month => {
            const monthData = yearData.months[month];
            const days = Object.keys(monthData.days).sort((a, b) => b.localeCompare(a));

            return (
              <div key={month} className="taxonomy-node">
                <TreeRow
                  galleryPath={galleryPath}
                  type="month"
                  value={monthValue({ year, month })}
                  name={monthName(month)}
                  count={monthData.count}
                />

                <div className="taxonomy-children">
                  {days.map(day => {
                    const parts = { year, month, day };
                    const dayData = monthData.days[day];
                    return (
                      <div key={day} className="taxonomy-node">
                        <TreeRow
                          galleryPath={galleryPath}
                          type="day"
                          value={dayValue(parts)}
                          name={formatDayLabel(parts)}
                          count={dayData.count}
                          thumbnails={dayData.photos}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  });
};

export default PhotoDateTree;
