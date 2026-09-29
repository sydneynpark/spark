// Fixed categorical order (blue, orange, aqua, yellow, magenta, green, violet,
// red) -- validated for adjacent CVD/contrast separation against this site's
// card background (#EAF0FF). Used only as each slider's accent color, purely
// decorative -- every row is already identified by its own name label.
const SLIDER_COLORS = [
  '#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948',
];

const TOTAL_WEIGHT = 100;

// A real weight is a share of TOTAL_WEIGHT split across `facetCount` facets,
// so an equal split sits at 1/facetCount -- with 7 facets that's ~14%, hard
// against the slider's left edge for every row at once. This computes the
// power-curve exponent that maps that equal-split fraction to exactly 0.5,
// for whatever facetCount currently is: solving (1/n)^p = 0.5 gives
// p = log(2)/log(n). At n=2 that's p=1 (already centered, no warp needed);
// for n>2 it's <1, which stretches everything below the equal split toward
// the middle and everything above it too -- values only reach the true
// edges as they approach the true extremes (0 or the full 100).
function displayExponent(facetCount) {
  return facetCount > 1 ? Math.log(2) / Math.log(facetCount) : 1;
}

// weightToPosition/positionToWeight are inverses of each other and are used
// ONLY to decide where the slider's thumb is drawn and how a drag maps back
// to a weight -- purely a display convenience. The weight value itself
// (used for redistribution math and for what gets submitted) is converted
// back to real units the moment a drag happens, via positionToWeight, and is
// never itself stored or calculated on this warped scale.
function weightToPosition(weight, facetCount) {
  const fraction = Math.min(Math.max(weight / TOTAL_WEIGHT, 0), 1);
  return Math.pow(fraction, displayExponent(facetCount)) * TOTAL_WEIGHT;
}

function positionToWeight(position, facetCount) {
  const fraction = Math.min(Math.max(position / TOTAL_WEIGHT, 0), 1);
  return Math.pow(fraction, 1 / displayExponent(facetCount)) * TOTAL_WEIGHT;
}

// One native range slider per facet, each 0-100 representing that facet's
// share of a fixed 100-point budget. Native sliders (rather than a custom
// drag surface) get correct touch behavior on every mobile browser for free.
// Moving one slider redistributes the difference across every other facet
// proportionally to their current shares -- like Humble Bundle's donation
// split sliders -- rather than only trading with a single neighbor.
function FacetWeightSliders({ facets, onWeightChange }) {
  if (facets.length === 0) return null;
  const facetCount = facets.length;

  return (
    <div className="admin-slider-list">
      {facets.map((facet, index) => (
        <div className="admin-slider-row" key={facet.id}>
          <span className="admin-slider-name">{facet.name || 'Untitled'}</span>
          <input
            type="range"
            min="0"
            max="100"
            step="any"
            value={weightToPosition(facet.weight, facetCount)}
            onChange={e => onWeightChange(facet.id, positionToWeight(Number(e.target.value), facetCount))}
            style={{ accentColor: SLIDER_COLORS[index % SLIDER_COLORS.length] }}
            disabled={facets.length < 2}
          />
          <span className="admin-slider-value">{Math.round(facet.weight)}%</span>
        </div>
      ))}
    </div>
  );
}

export default FacetWeightSliders;
