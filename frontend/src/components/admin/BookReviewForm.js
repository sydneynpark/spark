import { useState } from 'react';
import { Link } from 'react-router-dom';
import ApiService from '../../services/api';

const DEFAULT_FACET_NAMES = ['Characters', 'Atmosphere', 'Writing', 'Plot', 'Intrigue', 'Logic', 'Enjoyment'];
const DEFAULT_WEIGHT = 3;
const DEFAULT_RATING = 5;

let nextId = 0;
function newId(prefix) {
  nextId += 1;
  return `${prefix}-${nextId}`;
}

function makeDefaultFacets() {
  return DEFAULT_FACET_NAMES.map(name => ({
    id: newId('facet'),
    name,
    weight: DEFAULT_WEIGHT,
    rating: DEFAULT_RATING,
  }));
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function BookReviewForm() {
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

  function updateFacet(id, field, value) {
    setFacets(facets.map(f => (f.id === id ? { ...f, [field]: value } : f)));
  }

  function addFacet() {
    setFacets([...facets, { id: newId('facet'), name: '', weight: DEFAULT_WEIGHT, rating: DEFAULT_RATING }]);
  }

  function removeFacet(id) {
    setFacets(facets.filter(f => f.id !== id));
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
    setTitle('');
    setAuthor('');
    setDateReviewed(todayIso());
    setFacets(makeDefaultFacets());
    setTimelineEnabled(false);
    setTimeline([]);
    setOverallReview('');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (facets.length === 0) {
      setError('Add at least one facet.');
      return;
    }

    const payload = {
      title: title.trim(),
      author: author.trim(),
      date_reviewed: dateReviewed,
      rating_elements: facets.map(f => ({
        name: f.name.trim(),
        weight: Number(f.weight),
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
      setSuccess(result.status === 'published'
        ? `"${payload.title}" was published.`
        : (result.message || `"${payload.title}" was submitted.`));
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

      {error && <p className="error">{error}</p>}
      {success && <p className="admin-success">{success}</p>}

      <form className="admin-form" onSubmit={handleSubmit}>
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
          <p className="admin-form-hint">Name each facet, weight how important it is to the work, then score it out of 10.</p>
          <div className="admin-facet-list">
            <div className="admin-facet-row admin-facet-row--header">
              <span>Facet</span>
              <span>Weight</span>
              <span>Rating (0-10)</span>
              <span />
            </div>
            {facets.map(facet => (
              <div className="admin-facet-row" key={facet.id}>
                <input
                  type="text"
                  value={facet.name}
                  onChange={e => updateFacet(facet.id, 'name', e.target.value)}
                  placeholder="Facet name"
                  required
                />
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={facet.weight}
                  onChange={e => updateFacet(facet.id, 'weight', e.target.value)}
                  required
                />
                <input
                  type="number"
                  min="0"
                  max="10"
                  step="1"
                  value={facet.rating}
                  onChange={e => updateFacet(facet.id, 'rating', e.target.value)}
                  required
                />
                <button type="button" className="admin-remove-button" onClick={() => removeFacet(facet.id)}>Remove</button>
              </div>
            ))}
          </div>
          <button type="button" className="admin-add-button" onClick={addFacet}>+ Add Facet</button>
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

        <button type="submit" className="admin-submit-button" disabled={submitting}>
          {submitting ? 'Submitting...' : 'Submit Review'}
        </button>
      </form>
    </div>
  );
}

export default BookReviewForm;
