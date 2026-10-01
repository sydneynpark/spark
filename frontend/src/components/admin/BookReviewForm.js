import { useState } from 'react';
import { Link } from 'react-router-dom';
import ApiService from '../../services/api';
import FacetWeightSliders from './FacetWeightSliders';

const DEFAULT_FACET_NAMES = ['Characters', 'Atmosphere', 'Writing', 'Plot', 'Intrigue', 'Logic', 'Enjoyment'];
const DEFAULT_RATING = 5;

// Weights are a fixed 100-point budget split across facets (a "spend 100
// points on what matters" mental model) rather than arbitrary numbers --
// moving one facet's slider always redistributes the rest proportionally so
// they keep summing to 100. The backend doesn't require this (weighted_rating
// just divides by the total), it's purely a UI convention.
const TOTAL_WEIGHT = 100;
const MIN_WEIGHT = 0.1;

let nextId = 0;
function newId(prefix) {
  nextId += 1;
  return `${prefix}-${nextId}`;
}

function makeDefaultFacets() {
  const equalShare = TOTAL_WEIGHT / DEFAULT_FACET_NAMES.length;
  return DEFAULT_FACET_NAMES.map(name => ({
    id: newId('facet'),
    name,
    weight: equalShare,
    rating: DEFAULT_RATING,
  }));
}

// Weights are fractional while editing so the sliders move smoothly, but are
// stored as whole numbers. Plain rounding can drift off 100 (7 x 14.29 -> 98),
// so this floors everything and hands the leftover points to the facets with
// the largest fractional parts.
function roundWeightsToTotal(weights) {
  const floored = weights.map(w => Math.floor(w));
  let leftover = TOTAL_WEIGHT - floored.reduce((sum, w) => sum + w, 0);
  const byRemainder = weights
    .map((w, index) => ({ index, remainder: w - Math.floor(w) }))
    .sort((a, b) => b.remainder - a.remainder);
  for (const { index } of byRemainder) {
    if (leftover <= 0) break;
    floored[index] += 1;
    leftover -= 1;
  }
  return floored;
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function BookReviewForm() {
  const [step, setStep] = useState(1);
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [dateReviewed, setDateReviewed] = useState(todayIso);
  const [facets, setFacets] = useState(makeDefaultFacets);
  const [timelineEnabled, setTimelineEnabled] = useState(false);
  const [timeline, setTimeline] = useState([]);
  const [overallReview, setOverallReview] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  function updateFacetName(id, name) {
    setFacets(prev => prev.map(f => (f.id === id ? { ...f, name } : f)));
  }

  function updateFacetRating(id, rating) {
    setFacets(prev => prev.map(f => (f.id === id ? { ...f, rating } : f)));
  }

  // Moving one facet's slider takes/gives the difference from every other
  // facet, scaled by each one's current share of "everyone else" -- so a
  // facet that already had a small share stays small, one with a large share
  // gives up more, and the total always stays at 100.
  function handleWeightChange(id, newWeight) {
    setFacets(prev => {
      const changed = prev.find(f => f.id === id);
      if (!changed || prev.length < 2) return prev;

      const othersOldTotal = TOTAL_WEIGHT - changed.weight;
      const clampedNew = Math.min(
        Math.max(newWeight, MIN_WEIGHT),
        TOTAL_WEIGHT - MIN_WEIGHT * (prev.length - 1)
      );
      const othersNewTotal = TOTAL_WEIGHT - clampedNew;
      const scale = othersOldTotal > 0 ? othersNewTotal / othersOldTotal : 0;

      return prev.map(f => (
        f.id === id
          ? { ...f, weight: clampedNew }
          : { ...f, weight: Math.max(MIN_WEIGHT, f.weight * scale) }
      ));
    });
  }

  function addFacet() {
    const newShare = TOTAL_WEIGHT / (facets.length + 1);
    const scale = (TOTAL_WEIGHT - newShare) / TOTAL_WEIGHT;
    setFacets([
      ...facets.map(f => ({ ...f, weight: f.weight * scale })),
      { id: newId('facet'), name: '', weight: newShare, rating: DEFAULT_RATING },
    ]);
  }

  function removeFacet(id) {
    const removed = facets.find(f => f.id === id);
    const remaining = facets.filter(f => f.id !== id);
    if (!removed || remaining.length === 0) {
      setFacets(remaining);
      return;
    }
    const remainingOldTotal = TOTAL_WEIGHT - removed.weight;
    const scale = remainingOldTotal > 0 ? TOTAL_WEIGHT / remainingOldTotal : 1;
    setFacets(remaining.map(f => ({ ...f, weight: f.weight * scale })));
  }

  function updateTimelineEntry(id, field, value) {
    setTimeline(timeline.map(t => (t.id === id ? { ...t, [field]: value } : t)));
  }

  function addTimelineEntry() {
    setTimeline([...timeline, { id: newId('timeline'), point: 0, text: '' }]);
  }

  function removeTimelineEntry(id) {
    setTimeline(timeline.filter(t => t.id !== id));
  }

  function resetForm() {
    setStep(1);
    setTitle('');
    setAuthor('');
    setDateReviewed(todayIso());
    setFacets(makeDefaultFacets());
    setTimelineEnabled(false);
    setTimeline([]);
    setOverallReview('');
  }

  function handleNext(e) {
    e.preventDefault();
    setError(null);
    if (!title.trim() || !author.trim() || !dateReviewed) {
      setError('Fill in title, author, and date reviewed before continuing.');
      return;
    }
    if (facets.length === 0 || facets.some(f => !f.name.trim())) {
      setError('Every facet needs a name before continuing.');
      return;
    }
    setStep(2);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const weights = roundWeightsToTotal(facets.map(f => Number(f.weight)));
    const payload = {
      title: title.trim(),
      author: author.trim(),
      date_reviewed: dateReviewed,
      rating_elements: facets.map((f, index) => ({
        name: f.name.trim(),
        weight: weights[index],
        rating: Number(f.rating),
      })),
      commentary: timelineEnabled
        ? timeline.map(t => ({ point: Number(t.point), text: t.text.trim() })).filter(t => t.text)
        : [],
      overall_review: overallReview.trim(),
    };

    setSubmitting(true);
    try {
      const result = await ApiService.submitBookReview(payload);
      setSuccess(result.message || `"${payload.title}" was submitted.`);
      resetForm();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="admin-page admin-book-review-page">
      <Link to="/admin" className="back-link">← Back to Admin</Link>
      <h2>Upload Book Review</h2>
      <p className="admin-form-hint">Step {step} of 2: {step === 1 ? 'Define & weight facets' : 'Rate facets & add commentary'}</p>

      {error && <p className="error">{error}</p>}
      {success && <p className="admin-success">{success}</p>}

      {step === 1 && (
        <form className="admin-form" onSubmit={handleNext}>
          <div className="admin-form-row">
            <label>
              Title
              <input type="text" value={title} onChange={e => setTitle(e.target.value)} required />
            </label>
            <label>
              Author
              <input type="text" value={author} onChange={e => setAuthor(e.target.value)} required />
            </label>
            <label>
              Date Reviewed
              <input type="date" value={dateReviewed} onChange={e => setDateReviewed(e.target.value)} required />
            </label>
          </div>

          <section className="admin-form-section">
            <h3>Facets</h3>
            <p className="admin-form-hint">Name what goes into this review, then use the sliders below to weight how important each facet is -- moving one adjusts the others so they keep balancing to 100%. You'll rate them on the next step.</p>

            <div className="admin-facet-list">
              {facets.map(facet => (
                <div className="admin-facet-row" key={facet.id}>
                  <input
                    type="text"
                    value={facet.name}
                    onChange={e => updateFacetName(facet.id, e.target.value)}
                    placeholder="Facet name"
                    required
                  />
                  <button type="button" className="admin-remove-button" onClick={() => removeFacet(facet.id)}>Remove</button>
                </div>
              ))}
            </div>
            <button type="button" className="admin-add-button" onClick={addFacet}>+ Add Facet</button>

            <FacetWeightSliders facets={facets} onWeightChange={handleWeightChange} />
          </section>

          <button type="submit" className="admin-submit-button">Next: Rate Facets →</button>
        </form>
      )}

      {step === 2 && (
        <form className="admin-form" onSubmit={handleSubmit}>
          <section className="admin-form-section">
            <h3>Rate Each Facet</h3>
            <div className="admin-slider-list">
              {facets.map(facet => (
                <div className="admin-slider-row" key={facet.id}>
                  <span className="admin-slider-name">{facet.name}</span>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    step="1"
                    value={facet.rating}
                    onChange={e => updateFacetRating(facet.id, e.target.value)}
                  />
                  <span className="admin-slider-value">{facet.rating}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="admin-form-section">
            <label className="admin-checkbox-label">
              <input
                type="checkbox"
                checked={timelineEnabled}
                onChange={e => setTimelineEnabled(e.target.checked)}
              />
              Include a reading timeline
            </label>

            {timelineEnabled && (
              <div className="admin-timeline-list">
                {timeline.map(entry => (
                  <div className="admin-timeline-row" key={entry.id}>
                    <label className="admin-timeline-point">
                      %
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="1"
                        value={entry.point}
                        onChange={e => updateTimelineEntry(entry.id, 'point', e.target.value)}
                        required
                      />
                    </label>
                    <textarea
                      value={entry.text}
                      onChange={e => updateTimelineEntry(entry.id, 'text', e.target.value)}
                      placeholder="Thoughts at this point in the book"
                      rows={2}
                      required
                    />
                    <button type="button" className="admin-remove-button" onClick={() => removeTimelineEntry(entry.id)}>Remove</button>
                  </div>
                ))}
                <button type="button" className="admin-add-button" onClick={addTimelineEntry}>+ Add Timeline Entry</button>
              </div>
            )}
          </section>

          <section className="admin-form-section">
            <label>
              Overall Review <span className="admin-form-hint">(optional)</span>
              <textarea
                value={overallReview}
                onChange={e => setOverallReview(e.target.value)}
                rows={6}
                placeholder="Freetext thoughts on the book as a whole"
              />
            </label>
          </section>

          <div className="admin-form-actions">
            <button type="button" className="admin-back-button" onClick={() => setStep(1)}>← Back</button>
            <button type="submit" className="admin-submit-button" disabled={submitting}>
              {submitting ? 'Submitting...' : 'Submit Review'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default BookReviewForm;
