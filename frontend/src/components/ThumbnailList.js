import React from 'react';
import { Link } from 'react-router-dom';

// A list of clickable cards, each with a thumbnail beside its text, e.g. the
// book reviews and blog posts lists.
function ThumbnailList({ children }) {
  return <ul className="thumbnail-list">{children}</ul>;
}

// `shape` sizes the thumbnail: 'portrait' for book covers, 'landscape' for
// photos. A missing or broken `src` shows `placeholderSrc` instead.
export function ThumbnailListItem({ to, src, placeholderSrc, alt, shape = 'landscape', children }) {
  const thumbClass = `thumbnail-list-thumb thumbnail-list-thumb--${shape}`;
  return (
    <li className="thumbnail-list-item">
      <Link to={to}>
        <img
          className={`${thumbClass}${src ? '' : ' thumbnail-list-thumb--placeholder'}`}
          src={src || placeholderSrc}
          alt={alt}
          loading="lazy"
          onError={e => {
            if (e.target.src.endsWith(placeholderSrc)) return;
            e.target.src = placeholderSrc;
            e.target.classList.add('thumbnail-list-thumb--placeholder');
          }}
        />
        <div className="thumbnail-list-text">{children}</div>
      </Link>
    </li>
  );
}

export default ThumbnailList;
