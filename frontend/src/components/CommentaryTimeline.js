import ReactMarkdown from 'react-markdown';

function formatPoint(point) {
  return Number.isInteger(point) ? point : point.toFixed(1);
}

// Commentary tied to a point in the book (point is set) renders as a
// timeline in reading order; at most one item has no point and applies to
// the book as a whole, so it renders as free-floating text below.
function CommentaryTimeline({ commentary }) {
  const pointItems = commentary
    .filter((item) => item.point !== null && item.point !== undefined)
    .sort((a, b) => a.point - b.point);
  const overallItems = commentary.filter((item) => item.point === null || item.point === undefined);

  if (!pointItems.length && !overallItems.length) return null;

  return (
    <div className="commentary">
      {pointItems.length > 0 && (
        <ol className="commentary-timeline">
          {pointItems.map((item, index) => (
            <li key={index} className="commentary-timeline-item">
              <span className="commentary-timeline-badge">{formatPoint(item.point)}%</span>
              <div className="commentary-timeline-text">
                <ReactMarkdown>{item.text}</ReactMarkdown>
              </div>
            </li>
          ))}
        </ol>
      )}

      {overallItems.map((item, index) => (
        <div key={index} className="commentary-overall">
          <ReactMarkdown>{item.text}</ReactMarkdown>
        </div>
      ))}
    </div>
  );
}

export default CommentaryTimeline;
