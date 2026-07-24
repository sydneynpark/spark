import { useState } from 'react';

// Fixed-order categorical palette (validated for CVD-safe adjacency; see the
// dataviz skill). Slots are assigned by each rating element's position in
// the book review file, never re-assigned on hover/filter.
const CATEGORICAL_COLORS = [
  '#2a78d6', // blue
  '#eb6834', // orange
  '#1baf7a', // aqua
  '#eda100', // yellow
  '#e87ba4', // magenta
  '#008300', // green
  '#4a3aa7', // violet
  '#e34948', // red
];

const SIZE = 240;
const CENTER = SIZE / 2;
const MAX_RADIUS = 100;

function polarToCartesian(angleDeg, radius) {
  const angleRad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: CENTER + radius * Math.cos(angleRad),
    y: CENTER + radius * Math.sin(angleRad),
  };
}

// Angle = share of total weight (how important this element is to the
// book); radius = rating out of 10 (how well the book delivers on it),
// colored outward from the center.
function wedgePath(startAngle, endAngle, radius) {
  const start = polarToCartesian(startAngle, radius);
  const end = polarToCartesian(endAngle, radius);
  const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0;
  return [
    `M ${CENTER} ${CENTER}`,
    `L ${start.x} ${start.y}`,
    `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${end.x} ${end.y}`,
    'Z',
  ].join(' ');
}

function formatNumber(value) {
  return Number.isInteger(value) ? value : value.toFixed(1);
}

function RatingChart({ ratingElements }) {
  const [activeIndex, setActiveIndex] = useState(null);

  const totalWeight = ratingElements.reduce((sum, el) => sum + el.weight, 0);
  if (!ratingElements.length || totalWeight <= 0) return null;

  let cumulativeAngle = 0;
  const wedges = ratingElements.map((el, index) => {
    const angleSpan = (el.weight / totalWeight) * 360;
    const startAngle = cumulativeAngle;
    const endAngle = cumulativeAngle + angleSpan;
    cumulativeAngle = endAngle;
    return {
      ...el,
      index,
      startAngle,
      endAngle,
      radius: MAX_RADIUS * (el.rating / 10),
      color: CATEGORICAL_COLORS[index % CATEGORICAL_COLORS.length],
    };
  });

  const activate = (index) => () => setActiveIndex(index);
  const deactivate = () => setActiveIndex(null);

  return (
    <div className="rating-chart">
      <svg className="rating-chart-svg" viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label="Book rating chart">
        <circle className="rating-chart-outline" cx={CENTER} cy={CENTER} r={MAX_RADIUS} />
        {wedges.map((wedge) => {
          const label = `${wedge.name}: weight ${formatNumber(wedge.weight)}, rating ${formatNumber(wedge.rating)} out of 10`;
          const className = `rating-chart-wedge${activeIndex === wedge.index ? ' active' : ''}`;
          const commonProps = {
            fill: wedge.color,
            className,
            tabIndex: 0,
            role: 'img',
            'aria-label': label,
            onMouseEnter: activate(wedge.index),
            onMouseLeave: deactivate,
            onFocus: activate(wedge.index),
            onBlur: deactivate,
          };
          // A single rating element spans the full 360°, which degenerates
          // an SVG arc path (start and end points coincide); draw it as a
          // plain circle instead.
          return wedges.length === 1 ? (
            <circle key={wedge.index} cx={CENTER} cy={CENTER} r={wedge.radius} {...commonProps}>
              <title>{label}</title>
            </circle>
          ) : (
            <path key={wedge.index} d={wedgePath(wedge.startAngle, wedge.endAngle, wedge.radius)} {...commonProps}>
              <title>{label}</title>
            </path>
          );
        })}
      </svg>

      <ul className="rating-chart-legend">
        {wedges.map((wedge) => (
          <li
            key={wedge.index}
            className={`rating-chart-legend-item${activeIndex === wedge.index ? ' active' : ''}`}
            onMouseEnter={activate(wedge.index)}
            onMouseLeave={deactivate}
          >
            <span className="rating-chart-swatch" style={{ backgroundColor: wedge.color }} />
            <div className="rating-chart-legend-text">
              <span className="rating-chart-legend-name">{wedge.name}</span>
              <span className="rating-chart-legend-stats">
                Weight: {formatNumber(wedge.weight)} · Rating: {formatNumber(wedge.rating)}/10
              </span>
              {wedge.elaboration && <p className="rating-chart-legend-elaboration">{wedge.elaboration}</p>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default RatingChart;
