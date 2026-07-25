// A 5-point star, drawn once and reused as both the muted "empty" star and
// the colored "filled" one stacked on top of it.
const STAR_PATH = 'M12 1.5l3.22 6.53 7.2.98-5.21 5.09 1.23 7.17L12 17.77l-6.44 3.5 1.23-7.17-5.21-5.09 7.2-.98L12 1.5z';

function Star({ fill }) {
  return (
    <span className="star-rating-star">
      <svg className="star-rating-star-bg" viewBox="0 0 24 24" aria-hidden="true">
        <path d={STAR_PATH} />
      </svg>
      <span className="star-rating-star-fill" style={{ width: `${fill * 100}%` }}>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d={STAR_PATH} />
        </svg>
      </span>
    </span>
  );
}

// Ratings can land on quarter stars (see backend/src/utils/rating_util.py),
// so round-tripping through toFixed and back to a number is what drops the
// trailing zero from e.g. 4.50 -> "4.5" while still showing 4.25 in full.
function formatRating(rating) {
  return parseFloat(rating.toFixed(2));
}

function StarRating({ rating, className = '' }) {
  if (rating == null) return null;
  const fills = [0, 1, 2, 3, 4].map((i) => Math.max(0, Math.min(1, rating - i)));

  return (
    <span className={`star-rating ${className}`.trim()}>
      <span className="star-rating-stars" role="img" aria-label={`${formatRating(rating)} out of 5 stars`}>
        {fills.map((fill, i) => <Star key={i} fill={fill} />)}
      </span>
      <span className="star-rating-value" aria-hidden="true">{formatRating(rating)}</span>
    </span>
  );
}

export default StarRating;
