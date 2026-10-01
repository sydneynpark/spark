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
const PX_PER_DAY = 3;
const COVER_W = 36; // base size, for an unrated book
const COVER_H = 54;
const GAP_ABOVE = 10; // between the axis and covers above it
const GAP_BELOW = 26; // room for the month labels under the axis
const JITTER = 22; // how far a cover may drift from the axis on its own
const SEARCH_STEP = 7; // how far a crowded cover moves per placement attempt
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

// Each book gets a random preferred side, drift, and tilt. If that spot
// hides too much of an already-placed cover (or vice versa), it tries
// alternating sides at increasing distances until one is clear enough --
// so busy reading periods spread outward into a loose pile.
function scatter(dated) {
  const placed = [];
  dated.forEach(({ book, x }) => {
    const random = seededRandom(book.title);
    const preferred = random() < 0.5 ? 'above' : 'below';
    const other = preferred === 'above' ? 'below' : 'above';
    const drift = random() * JITTER;
    const tilt = (random() * 2 - 1) * MAX_TILT;
    const { w, h } = coverSize(book.star_rating);
    const left = x - w / 2;

    for (let step = 0; ; step++) {
      const offset = drift + step * SEARCH_STEP;
      const spot = [preferred, other]
        .map(side => ({ side, left, top: coverTop(side, offset, h), w, h }))
        .find(candidate => placed.every(p => overlapShare(p, candidate) <= MAX_OVERLAP));
      if (spot) {
        placed.push({ book, x, tilt, ...spot });
        return;
      }
    }
  });
  return placed;
}

// Lays the books out on a time axis running from the first month with a
// review through today.
function layoutShelf(books) {
  const withDates = books.filter(book => book.date_reviewed);
  if (!withDates.length) return null;

  const days = withDates.map(book => toDay(book.date_reviewed));
  const first = new Date(Math.min(...days) * DAY_MS);
  const startDay = Date.UTC(first.getUTCFullYear(), first.getUTCMonth(), 1) / DAY_MS;
  const endDay = Math.max(...days, todayDay());
  const xOf = day => EDGE_PAD + (day - startDay) * PX_PER_DAY;

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
  const layout = useMemo(() => layoutShelf(books), [books]);
  const scrollRef = useRef(null);
  const [activeTitle, setActiveTitle] = useState(null);

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
