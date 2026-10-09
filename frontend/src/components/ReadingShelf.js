import React, { useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import ApiService from '../services/api';

// A cover's area scales with its 0-5 star rating, from MIN_AREA x the base
// cover at 1 star or below up to MAX_AREA x at 5 stars. Scaling area rather
// than width matches how size is perceived, so 5 stars doesn't loom.
const MIN_AREA = 0.5;
const MAX_AREA = 1.8;

// On top of size, duds (0-2 stars) fade out and standouts (4.5-5) glow.
// Star ratings are discrete (see backend/src/utils/rating_util.py), so these
// line up with real values.
const DUD_MAX = 2.0;
const STANDOUT_MIN = 4.5;

// Geometry, in px. Each cover is centered horizontally on its exact review
// date; its vertical position is a deliberately meaningless scatter above
// or below the axis, kept clear of the axis labels.
const MIN_PX_PER_DAY = 3; // stretched further if the shelf has room to spare
const COVER_W = 36; // base size, for an unrated book
const COVER_H = 54;
const GAP_ABOVE = 10; // between the axis and covers above it
const GAP_BELOW = 26; // room for the month labels under the axis
const BAND = 130; // depth of the scatter band on each side of the axis
const RANDOM_TRIES = 12; // random spots in the bands tried before overflowing
const SEARCH_STEP = 7; // how far an overflowing cover moves per attempt
const MAX_OVERLAP = 0.2; // share of the smaller cover a larger one may hide
const MAX_TILT = 7; // degrees
const EDGE_PAD = 28;
const OUTER_PAD = 18; // room for the standout glow and tilted corners

const DAY_MS = 24 * 60 * 60 * 1000;
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function toDay(dateStr) {
  const [year, month, day] = dateStr.split('-').map(Number);
  return Date.UTC(year, month - 1, day) / DAY_MS;
}

function todayDay() {
  const now = new Date();
  return Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) / DAY_MS;
}

function ratingClass(rating) {
  if (rating == null) return '';
  if (rating <= DUD_MAX) return ' reading-shelf-book--dud';
  if (rating >= STANDOUT_MIN) return ' reading-shelf-book--standout';
  return '';
}

function coverSize(rating) {
  if (rating == null) return { w: COVER_W, h: COVER_H };
  const t = Math.max(0, Math.min(1, (rating - 1) / 4));
  const scale = Math.sqrt(MIN_AREA + t * (MAX_AREA - MIN_AREA));
  return { w: COVER_W * scale, h: COVER_H * scale };
}

function formatShortDate(dateStr) {
  const [year, month, day] = dateStr.split('-').map(Number);
  return `${MONTHS[month - 1]} ${day}, ${year}`;
}

// Seeded from the title, so each book lands in the same spot on every load.
function seededRandom(str) {
  let seed = 2166136261;
  for (let i = 0; i < str.length; i++) {
    seed = Math.imul(seed ^ str.charCodeAt(i), 16777619);
  }
  return () => {
    seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function overlapShare(a, b) {
  const w = Math.min(a.left + a.w, b.left + b.w) - Math.max(a.left, b.left);
  const h = Math.min(a.top + a.h, b.top + b.h) - Math.max(a.top, b.top);
  return w > 0 && h > 0 ? (w * h) / Math.min(a.w * a.h, b.w * b.h) : 0;
}

// Top edge (relative to the axis) of a cover of height h pushed `offset` px
// away from the axis on the given side.
function coverTop(side, offset, h) {
  return side === 'above' ? -GAP_ABOVE - offset - h : GAP_BELOW + offset;
}

// Every cover lands at a random depth within the band on a random side of
// the axis -- whether or not it has neighbors, so height reads as scatter
// rather than as a sign of a busy reading period. If a spot hides too much
// of an already-placed cover (or vice versa), it tries more random spots in
// both bands; only if those are all taken does it overflow past the band,
// alternating sides at increasing distances.
function scatter(dated) {
  const placed = [];
  dated.forEach(({ book, x }) => {
    const random = seededRandom(book.title);
    const tilt = (random() * 2 - 1) * MAX_TILT;
    const { w, h } = coverSize(book.star_rating);
    const left = x - w / 2;
    const room = Math.max(0, BAND - h);
    const at = (side, offset) => ({ side, left, top: coverTop(side, offset, h), w, h });
    const fits = spot => placed.every(p => overlapShare(p, spot) <= MAX_OVERLAP);

    let spot;
    for (let i = 0; i < RANDOM_TRIES && !spot; i++) {
      const candidate = at(random() < 0.5 ? 'above' : 'below', random() * room);
      if (fits(candidate)) spot = candidate;
    }
    for (let step = 1; !spot; step++) {
      spot = [at('above', room + step * SEARCH_STEP), at('below', room + step * SEARCH_STEP)].find(fits);
    }
    placed.push({ book, x, tilt, ...spot });
  });
  return placed;
}

// The time axis runs from the first month with a review through today.
function shelfRange(books) {
  const withDates = books.filter(book => book.date_reviewed);
  if (!withDates.length) return null;

  const days = withDates.map(book => toDay(book.date_reviewed));
  const first = new Date(Math.min(...days) * DAY_MS);
  return {
    withDates,
    startDay: Date.UTC(first.getUTCFullYear(), first.getUTCMonth(), 1) / DAY_MS,
    endDay: Math.max(...days, todayDay()),
  };
}

// The scale that stretches the axis across the shelf's full width, unless
// that's below MIN_PX_PER_DAY -- then the shelf scrolls instead.
function pxPerDayFor({ startDay, endDay }, shelfWidth) {
  const stretched = (shelfWidth - 2 * EDGE_PAD) / Math.max(1, endDay - startDay);
  return Math.max(MIN_PX_PER_DAY, stretched);
}

// Lays the books out along the axis at the given scale.
function layoutShelf({ withDates, startDay, endDay }, pxPerDay) {
  const xOf = day => EDGE_PAD + (day - startDay) * pxPerDay;

  const dated = withDates
    .map(book => ({ book, day: toDay(book.date_reviewed) }))
    .sort((a, b) => a.day - b.day || a.book.title.localeCompare(b.book.title))
    .map(({ book, day }) => ({ book, x: xOf(day) }));
  const placed = scatter(dated);

  const ticks = [];
  for (let d = new Date(startDay * DAY_MS); d.getTime() / DAY_MS <= endDay;
    d = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1))) {
    const month = d.getUTCMonth();
    ticks.push({
      key: `${d.getUTCFullYear()}-${month}`,
      x: xOf(d.getTime() / DAY_MS),
      label: month === 0 || !ticks.length ? `${MONTHS[month]} ${d.getUTCFullYear()}` : MONTHS[month],
      major: month === 0,
    });
  }

  // Covers' tops are relative to the axis; shift everything down so the
  // highest cover clears the top of the track.
  const highest = Math.min(-GAP_ABOVE, ...placed.map(p => p.top));
  const lowest = Math.max(GAP_BELOW, ...placed.map(p => p.top + p.h));
  const axisY = OUTER_PAD - highest;

  return {
    placed,
    ticks,
    axisY,
    todayX: xOf(todayDay()),
    width: xOf(endDay) + EDGE_PAD,
    height: axisY + lowest + OUTER_PAD,
  };
}

function ReadingShelf({ books }) {
  const range = useMemo(() => shelfRange(books), [books]);
  const [shelfWidth, setShelfWidth] = useState(0);
  // Memoized on the scale rather than the width, so resizing while it's
  // pinned at MIN_PX_PER_DAY doesn't redo the layout or reset the scroll.
  const pxPerDay = range ? pxPerDayFor(range, shelfWidth) : MIN_PX_PER_DAY;
  const layout = useMemo(() => range && layoutShelf(range, pxPerDay), [range, pxPerDay]);
  const scrollRef = useRef(null);
  const [activeTitle, setActiveTitle] = useState(null);

  // Track the shelf's width, so the axis can stretch to fill it.
  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return undefined;
    const measure = () => setShelfWidth(el.clientWidth);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, [range]);

  // Open scrolled to the newest end of the shelf.
  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollLeft = el.scrollWidth;
  }, [layout]);

  if (!layout) return null;
  const { placed, ticks, axisY, todayX, width, height } = layout;

  return (
    <div className="reading-shelf" ref={scrollRef}>
      <div className="reading-shelf-track" style={{ width, height }}>
        <div className="reading-shelf-axis" style={{ top: axisY }} />
        {ticks.map(tick => (
          <div
            key={tick.key}
            className={`reading-shelf-tick${tick.major ? ' reading-shelf-tick--major' : ''}`}
            style={{ left: tick.x, top: axisY }}
          >
            <span>{tick.label}</span>
          </div>
        ))}
        <div className="reading-shelf-today" style={{ left: todayX, top: axisY }} title="Today" />

        {placed.map(({ book, x, top, h }) => {
          const active = activeTitle === book.title;
          const coverMiddle = top + h / 2;
          return (
            <React.Fragment key={book.title}>
              <div
                className={`reading-shelf-stem${active ? ' reading-shelf-stem--active' : ''}`}
                style={{ left: x, top: axisY + Math.min(0, coverMiddle), height: Math.abs(coverMiddle) }}
              />
              <div className={`reading-shelf-mark${active ? ' reading-shelf-mark--active' : ''}`} style={{ left: x, top: axisY }} />
            </React.Fragment>
          );
        })}

        {placed.map(({ book, side, left, top, w, h, tilt }) => {
          const stars = book.star_rating != null ? `${parseFloat(book.star_rating.toFixed(2))} stars` : null;
          const activate = () => setActiveTitle(book.title);
          const deactivate = () => setActiveTitle(null);
          return (
            <Link
              key={book.title}
              to={`/books/${encodeURIComponent(book.title)}`}
              className={`reading-shelf-book reading-shelf-book--${side}${ratingClass(book.star_rating)}`}
              style={{ left, top: axisY + top, width: w, height: h, '--tilt': `${tilt}deg` }}
              aria-label={`${book.title}, read ${formatShortDate(book.date_reviewed)}${stars ? `, ${stars}` : ''}`}
              onMouseEnter={activate}
              onMouseLeave={deactivate}
              onFocus={activate}
              onBlur={deactivate}
            >
              <img
                src={book.cover_key ? ApiService.getBookCoverUrl(book.cover_key) : '/images/placeholder-book.jpg'}
                alt=""
                loading="lazy"
                onError={e => { e.target.src = '/images/placeholder-book.jpg'; }}
              />
              <span className="reading-shelf-tooltip" aria-hidden="true">
                <strong>{book.title}</strong>
                <span>{formatShortDate(book.date_reviewed)}{stars && ` · ${stars}`}</span>
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

export default ReadingShelf;
