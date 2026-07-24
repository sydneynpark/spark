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

const MAX_RATING = 10;
const RING_STEPS = [2, 4, 6, 8, 10];

const OUTER_RADIUS = 92;
const LABEL_GAP = 16;
const LABEL_DOT_RADIUS = 3;
const CORNER_RADIUS = 5;
const CHART_PADDING = 130;
const SIZE = (OUTER_RADIUS + CHART_PADDING) * 2;
const CENTER = SIZE / 2;

function polarToCartesian(angleDeg, radius) {
  const angleRad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: CENTER + radius * Math.cos(angleRad),
    y: CENTER + radius * Math.sin(angleRad),
  };
}

// A pie-shaped wedge (apex at the center) with its two outer corners
// rounded, so each sector reads as a soft radial bar rather than a slice.
// The corner is approximated with a quadratic bezier using the sharp
// corner itself as the control point — a common, cheap fillet that looks
// right without solving for a true tangent circle.
function wedgePath(startAngle, endAngle, radius) {
  if (radius <= 0) return '';
  const span = endAngle - startAngle;
  if (span >= 360) {
    // Full circle: draw as two arcs, no corners to round.
    const top = polarToCartesian(startAngle, radius);
    const bottom = polarToCartesian(startAngle + 180, radius);
    return [
      `M ${top.x} ${top.y}`,
      `A ${radius} ${radius} 0 1 1 ${bottom.x} ${bottom.y}`,
      `A ${radius} ${radius} 0 1 1 ${top.x} ${top.y}`,
      'Z',
    ].join(' ');
  }

  const r = Math.min(CORNER_RADIUS, radius / 2);
  const cornerAngle = Math.min((r / radius) * (180 / Math.PI), span / 2);
  const a0 = startAngle + cornerAngle;
  const a1 = endAngle - cornerAngle;

  const startCorner = polarToCartesian(startAngle, radius);
  const startPullback = polarToCartesian(startAngle, radius - r);
  const startFillet = polarToCartesian(a0, radius);
  const endFillet = polarToCartesian(a1, radius);
  const endCorner = polarToCartesian(endAngle, radius);
  const endPullback = polarToCartesian(endAngle, radius - r);
  const largeArcFlag = a1 - a0 > 180 ? 1 : 0;

  return [
    `M ${CENTER} ${CENTER}`,
    `L ${startPullback.x} ${startPullback.y}`,
    `Q ${startCorner.x} ${startCorner.y} ${startFillet.x} ${startFillet.y}`,
    `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${endFillet.x} ${endFillet.y}`,
    `Q ${endCorner.x} ${endCorner.y} ${endPullback.x} ${endPullback.y}`,
    'Z',
  ].join(' ');
}

function formatNumber(value) {
  return Number.isInteger(value) ? value : value.toFixed(1);
}

// Radial labels stay flat (no rotation) so they're always legible; only
// which side of the dot the text sits on changes, so it extends away from
// the circle instead of back over it.
function labelTransform(midAngle) {
  const flip = midAngle > 180 && midAngle < 360;
  return { anchor: flip ? 'end' : 'start' };
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
    const midAngle = (startAngle + endAngle) / 2;
    return {
      ...el,
      index,
      startAngle,
      endAngle,
      midAngle,
      radius: OUTER_RADIUS * (el.rating / MAX_RATING),
      color: CATEGORICAL_COLORS[index % CATEGORICAL_COLORS.length],
    };
  });

  const hasElaborations = wedges.some((w) => w.elaboration);
  const activate = (index) => () => setActiveIndex(index);
  const deactivate = () => setActiveIndex(null);

  return (
    <div className="rating-chart">
      <svg
        className="rating-chart-svg"
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role="img"
        aria-label="Book rating chart"
      >
        {RING_STEPS.map((step) => (
          <circle
            key={step}
            className="rating-chart-ring"
            cx={CENTER}
            cy={CENTER}
            r={OUTER_RADIUS * (step / MAX_RATING)}
          />
        ))}

        {wedges.map((wedge) => (
          <path
            key={`track-${wedge.index}`}
            className="rating-chart-track"
            style={{ '--wedge-color': wedge.color }}
            d={wedgePath(wedge.startAngle, wedge.endAngle, OUTER_RADIUS)}
          />
        ))}

        {wedges.map((wedge) => {
          const label = `${wedge.name}: weight ${formatNumber(wedge.weight)}, rating ${formatNumber(wedge.rating)} out of ${MAX_RATING}`;
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
          if (wedge.radius <= 0) return null;
          return (
            <path key={wedge.index} d={wedgePath(wedge.startAngle, wedge.endAngle, wedge.radius)} {...commonProps}>
              <title>{label}</title>
            </path>
          );
        })}

        {wedges.map((wedge) => {
          const anchorPoint = polarToCartesian(wedge.midAngle, OUTER_RADIUS + LABEL_GAP);
          const { anchor } = labelTransform(wedge.midAngle);
          const textStart = anchorPoint.x + (anchor === 'end' ? -1 : 1) * (LABEL_DOT_RADIUS + 6);
          return (
            <g
              key={`label-${wedge.index}`}
              className={`rating-chart-label${activeIndex === wedge.index ? ' active' : ''}`}
              aria-hidden="true"
            >
              <circle cx={anchorPoint.x} cy={anchorPoint.y} r={LABEL_DOT_RADIUS} fill={wedge.color} />
              <text x={textStart} y={anchorPoint.y} textAnchor={anchor} className="rating-chart-label-name">
                {wedge.name}
              </text>
              <text x={textStart} y={anchorPoint.y} dy="1.15em" textAnchor={anchor} className="rating-chart-label-rating">
                {formatNumber(wedge.rating)}/{MAX_RATING}
              </text>
            </g>
          );
        })}
      </svg>

      {hasElaborations && (
        <ul className="rating-chart-notes">
          {wedges.filter((w) => w.elaboration).map((wedge) => (
            <li
              key={wedge.index}
              className={`rating-chart-note${activeIndex === wedge.index ? ' active' : ''}`}
              onMouseEnter={activate(wedge.index)}
              onMouseLeave={deactivate}
            >
              <span className="rating-chart-swatch" style={{ backgroundColor: wedge.color }} />
              <div className="rating-chart-note-text">
                <span className="rating-chart-note-name">{wedge.name}</span>
                <p className="rating-chart-note-elaboration">{wedge.elaboration}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default RatingChart;
