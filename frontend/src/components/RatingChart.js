import { useState, useEffect } from 'react';

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
// Facets weighted below this share of the total aren't drawn (see below).
const MIN_SHARE = 0.01;

const LABEL_GAP = 16;
const LABEL_DOT_RADIUS = 3;
const CORNER_RADIUS = 5;

// Below this viewport width, the always-on radial labels (sized for the
// longest label text) are dropped in favor of a single tap-to-reveal
// caption, so the ring can claim nearly the whole box instead of most of
// it being reserved margin the labels would otherwise get clipped into.
const COMPACT_BREAKPOINT = 600;
// chartPadding is the room beside the ring for direct labels, which extend
// sideways from their dot; labels above/below the ring only need a couple of
// text lines, so verticalPadding crops the otherwise-square box down to that
// instead of leaving the same 120px empty above and below the chart.
const GEOMETRY = {
  full: { outerRadius: 110, chartPadding: 120, verticalPadding: 48 },
  compact: { outerRadius: 130, chartPadding: 24, verticalPadding: 24 },
};

function useCompactLayout() {
  const [compact, setCompact] = useState(
    () => typeof window !== 'undefined' && window.innerWidth <= COMPACT_BREAKPOINT
  );

  useEffect(() => {
    const query = window.matchMedia(`(max-width: ${COMPACT_BREAKPOINT}px)`);
    const update = (e) => setCompact(e.matches);
    update(query);
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);

  return compact;
}

function polarToCartesian(angleDeg, radius, center) {
  const angleRad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: center + radius * Math.cos(angleRad),
    y: center + radius * Math.sin(angleRad),
  };
}

// A pie-shaped wedge (apex at the center) with its two outer corners
// rounded, so each sector reads as a soft radial bar rather than a slice.
// The corner is approximated with a quadratic bezier using the sharp
// corner itself as the control point — a common, cheap fillet that looks
// right without solving for a true tangent circle.
function wedgePath(startAngle, endAngle, radius, center) {
  if (radius <= 0) return '';
  const span = endAngle - startAngle;
  if (span >= 360) {
    // Full circle: draw as two arcs, no corners to round.
    const top = polarToCartesian(startAngle, radius, center);
    const bottom = polarToCartesian(startAngle + 180, radius, center);
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

  const startCorner = polarToCartesian(startAngle, radius, center);
  const startPullback = polarToCartesian(startAngle, radius - r, center);
  const startFillet = polarToCartesian(a0, radius, center);
  const endFillet = polarToCartesian(a1, radius, center);
  const endCorner = polarToCartesian(endAngle, radius, center);
  const endPullback = polarToCartesian(endAngle, radius - r, center);
  const largeArcFlag = a1 - a0 > 180 ? 1 : 0;

  return [
    `M ${center} ${center}`,
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

// Font sizes match .rating-chart-label-name / -rating in App.css. Rough
// per-character widths are the fallback when canvas measuring isn't
// available (e.g. tests) -- deliberately generous, since overestimating only
// drops a label the legend already covers, while underestimating overlaps.
const LABEL_NAME_FONT = '600 15px';
const LABEL_RATING_FONT = '12px';
const LABEL_LINE_ABOVE = 12;
const LABEL_LINE_BELOW = 22;

let measureContext;
function measureText(text, font, fallbackCharWidth) {
  if (measureContext === undefined) {
    measureContext = typeof document !== 'undefined'
      ? document.createElement('canvas').getContext('2d')
      : null;
  }
  if (!measureContext) return text.length * fallbackCharWidth;
  const family = getComputedStyle(document.body).fontFamily || 'sans-serif';
  measureContext.font = `${font} ${family}`;
  return measureContext.measureText(text).width;
}

// Direct labels are a supplement to the legend, so a label only goes on the
// ring when it has room. Bigger slices claim their spot first; any label that
// would overlap one already placed is left off (that facet is still in the
// legend and highlights on hover). The same goes for a label too long to
// fit beside the ring without being clipped by the chart's edge. Nudging labels apart instead detaches
// them from thin slices and, for a cluster of slivers, still ends in a pile.
function placeLabels(wedges, outerRadius, center, bounds) {
  const placed = [];
  const byWeight = [...wedges].sort((a, b) => b.weight - a.weight);
  for (const wedge of byWeight) {
    const anchorPoint = polarToCartesian(wedge.midAngle, outerRadius + LABEL_GAP, center);
    const { anchor } = labelTransform(wedge.midAngle);
    const direction = anchor === 'end' ? -1 : 1;
    const textStart = anchorPoint.x + direction * (LABEL_DOT_RADIUS + 6);
    const textWidth = Math.max(
      measureText(wedge.name, LABEL_NAME_FONT, 9.5),
      measureText(`${formatNumber(wedge.rating)}/${MAX_RATING}`, LABEL_RATING_FONT, 7.5)
    );
    const xs = [anchorPoint.x - direction * LABEL_DOT_RADIUS, textStart + direction * textWidth];
    const box = {
      left: Math.min(...xs),
      right: Math.max(...xs),
      top: anchorPoint.y - LABEL_LINE_ABOVE,
      bottom: anchorPoint.y + LABEL_LINE_BELOW,
    };
    const outOfBounds = box.left < bounds.left || box.right > bounds.right
      || box.top < bounds.top || box.bottom > bounds.bottom;
    const collides = outOfBounds || placed.some(({ box: other }) => (
      box.left < other.right && box.right > other.left && box.top < other.bottom && box.bottom > other.top
    ));
    if (!collides) placed.push({ wedge, anchorPoint, anchor, textStart, box });
  }
  return placed;
}

function RatingChart({ ratingElements }) {
  const [activeIndex, setActiveIndex] = useState(null);
  const compact = useCompactLayout();
  const {
    outerRadius: OUTER_RADIUS,
    chartPadding: CHART_PADDING,
    verticalPadding: VERTICAL_PADDING,
  } = compact ? GEOMETRY.compact : GEOMETRY.full;
  const SIZE = (OUTER_RADIUS + CHART_PADDING) * 2;
  const CENTER = SIZE / 2;
  // All the geometry is laid out in a SIZE x SIZE square around CENTER; the
  // viewBox just crops its top and bottom.
  const HEIGHT = (OUTER_RADIUS + VERTICAL_PADDING) * 2;
  const TOP = CENTER - HEIGHT / 2;

  // Weights can be on any scale (e.g. 1-5 per facet, or a 100-point budget),
  // so "too small to draw" is judged by share of the total, not raw weight.
  // A facet under MIN_SHARE wouldn't produce a visible slice, so it's left
  // out of the chart and legend entirely (it still counts toward the book's
  // overall rating). Each facet keeps its original index so its color stays
  // the same whether or not a neighbor was omitted.
  const totalWeight = ratingElements.reduce((sum, el) => sum + el.weight, 0);
  if (!ratingElements.length || totalWeight <= 0) return null;
  const shown = ratingElements
    .map((el, index) => ({ el, index }))
    .filter(({ el }) => el.weight / totalWeight >= MIN_SHARE);
  const shownWeight = shown.reduce((sum, { el }) => sum + el.weight, 0);

  let cumulativeAngle = 0;
  const wedges = shown.map(({ el, index }) => {
    const angleSpan = (el.weight / shownWeight) * 360;
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

  const labels = compact ? [] : placeLabels(wedges, OUTER_RADIUS, CENTER, {
    left: 0, right: SIZE, top: TOP, bottom: TOP + HEIGHT,
  });
  const activeWedge = wedges.find((w) => w.index === activeIndex) ?? null;
  const activate = (index) => () => setActiveIndex(index);
  const deactivate = () => setActiveIndex(null);

  return (
    <div className="rating-chart">
      <svg
        className="rating-chart-svg"
        viewBox={`0 ${TOP} ${SIZE} ${HEIGHT}`}
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

        {/* The track carries the interaction: it's always opaque and always spans the
            full (untrimmed) sector, so it's a reliable hit target everywhere in the
            slice — unlike the rating-scaled colored fill above it, which for a low
            rating can be a sliver too small to tap accurately, especially on a phone. */}
        {wedges.map((wedge) => {
          const label = `${wedge.name}: weight ${formatNumber(wedge.weight)}, rating ${formatNumber(wedge.rating)} out of ${MAX_RATING}`;
          return (
            <path
              key={`track-${wedge.index}`}
              className="rating-chart-track"
              style={{ '--wedge-color': wedge.color }}
              d={wedgePath(wedge.startAngle, wedge.endAngle, OUTER_RADIUS, CENTER)}
              tabIndex={0}
              role="img"
              aria-label={label}
              onMouseEnter={activate(wedge.index)}
              onMouseLeave={deactivate}
              onFocus={activate(wedge.index)}
              onBlur={deactivate}
              onClick={activate(wedge.index)}
            >
              <title>{label}</title>
            </path>
          );
        })}

        {/* Purely decorative overlay — pointer-events: none lets taps pass through to
            the track underneath instead of being swallowed here. */}
        {wedges.map((wedge) => {
          if (wedge.radius <= 0) return null;
          const className = `rating-chart-wedge${activeIndex === wedge.index ? ' active' : ''}`;
          return (
            <path
              key={wedge.index}
              aria-hidden="true"
              fill={wedge.color}
              className={className}
              style={{ pointerEvents: 'none' }}
              d={wedgePath(wedge.startAngle, wedge.endAngle, wedge.radius, CENTER)}
            />
          );
        })}

        {labels.map(({ wedge, anchorPoint, anchor, textStart }) => (
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
        ))}
      </svg>

      {compact && (
        <p className="rating-chart-caption" aria-live="polite">
          {activeWedge ? (
            <>
              <span
                className="rating-chart-caption-swatch"
                style={{ backgroundColor: activeWedge.color }}
                aria-hidden="true"
              />
              <span className="rating-chart-caption-name">{activeWedge.name}</span>
              <span className="rating-chart-caption-rating">
                {formatNumber(activeWedge.rating)}/{MAX_RATING}
              </span>
            </>
          ) : (
            <span className="rating-chart-caption-hint">Tap a slice for details</span>
          )}
        </p>
      )}

      {/* The legend: every facet with its rating (and elaboration, if the review
          has one), so identity never depends on a direct label fitting on the ring. */}
      <ul className="rating-chart-notes">
        {wedges.map((wedge) => (
          <li
            key={wedge.index}
            className={`rating-chart-note${activeIndex === wedge.index ? ' active' : ''}`}
            onMouseEnter={activate(wedge.index)}
            onMouseLeave={deactivate}
          >
            <span className="rating-chart-swatch" style={{ backgroundColor: wedge.color }} />
            <div className="rating-chart-note-text">
              <span className="rating-chart-note-name">
                {wedge.name}
                <span className="rating-chart-note-rating">{formatNumber(wedge.rating)}/{MAX_RATING}</span>
              </span>
              {wedge.elaboration && <p className="rating-chart-note-elaboration">{wedge.elaboration}</p>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default RatingChart;
