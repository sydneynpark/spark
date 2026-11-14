import { useState, useEffect, useCallback, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import ApiService from '../services/api';
import seededRandom from '../utils/seededRandom';

// photo://<key> embeds name a photo by its key in this bucket, e.g.
// photo://birds/2026/05/23/<photo>.jpg or photo://photos/2026/07/04/<photo>.jpg.
const PHOTOS_BUCKET = 'spark.wiki.photos';

// 'YYYY-MM-DD', as a post's date reads at the top of it.
export function formatPostDate(dateStr) {
  const [year, month, day] = dateStr.split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  });
}

// A post's dates, as they read at the top of it: the one it's shown under,
// and when it was written, if that was later (or earlier).
export function PostDates({ date, written }) {
  if (!date) return null;
  return (
    <>
      <time className="post-date" dateTime={date}>{formatPostDate(date)}</time>
      {written && written !== date && (
        <span className="post-date post-written">
          {' · Written '}<time dateTime={written}>{formatPostDate(written)}</time>
        </span>
      )}
    </>
  );
}

const SWIPE_THRESHOLD = 50;

// Embeds are laid out like a scrapbook: each photo tilts a little (leaning
// the other way from its neighbor in a row; see App.css), is drawn a little
// bigger or smaller, and sits a little higher or lower -- by amounts seeded
// from its key, so it lands the same way on every load.
const MIN_TILT = 1; // degrees
const MAX_TILT = 6;
const MIN_SCALE = 0.88;
const MAX_SCALE = 1.08;

function scrapbookStyle(key) {
  const random = seededRandom(key);
  const tilt = MIN_TILT + random() * (MAX_TILT - MIN_TILT);
  const scale = MIN_SCALE + random() * (MAX_SCALE - MIN_SCALE);
  const nudge = random() * 2 - 1;
  return {
    '--tilt': `${tilt}deg`,
    '--photo-scale': scale,
    '--nudge': nudge,
  };
}

// Photos of every shape are drawn about the same area, so a portrait doesn't
// look smaller than a landscape beside it: the size a 3:2 landscape is drawn
// at is scaled by how much taller or shorter the photo is for the same area,
// within limits for extreme panoramas or verticals. Until a photo has loaded
// and its shape is known, it's drawn as a 3:2 landscape.
const BASE_ASPECT = 3 / 2;
const MIN_SIZE = 0.7;
const MAX_SIZE = 1.5;

function sizeForAspect(aspect) {
  return Math.min(MAX_SIZE, Math.max(MIN_SIZE, Math.sqrt(BASE_ASPECT / aspect)));
}

// Each photo's width / height by its URL, once loaded. Embeds are re-created
// whenever the post re-renders (e.g. when the lightbox opens); remembering
// their shapes keeps them from jumping back to the 3:2 size meanwhile.
const aspectsBySrc = new Map();

// One photo embed: its thumbnail, scrapbook style, which opens it full size.
function PhotoEmbed({ photoKey, src, fullsize, onOpen }) {
  const [aspect, setAspect] = useState(() => aspectsBySrc.get(src));

  const handleLoad = (e) => {
    const { naturalWidth, naturalHeight } = e.currentTarget;
    if (!naturalWidth || !naturalHeight) return;
    const loaded = naturalWidth / naturalHeight;
    aspectsBySrc.set(src, loaded);
    setAspect(loaded);
  };

  const style = {
    ...scrapbookStyle(photoKey),
    '--photo-size': aspect ? sizeForAspect(aspect) : 1,
  };
  return (
    <span
      className="blog-photo-embed"
      style={style}
      data-fullsize={fullsize}
      onClick={e => onOpen(e.currentTarget)}
    >
      <img src={src} alt="Photo" onLoad={handleLoad} />
    </span>
  );
}

function isPhotoEmbed(node) {
  return node.type === 'element' && node.tagName === 'code' && node.children.length === 1
    && node.children[0].type === 'text' && node.children[0].value.trim().startsWith('photo://');
}

// A paragraph of nothing but photo embeds, e.g. one per line: laid out as a
// scrapbook row of photos rather than as text.
function isPhotoRow(node) {
  const embeds = node.children.filter(child => !(child.type === 'text' && !child.value.trim()));
  return embeds.length > 0 && embeds.every(isPhotoEmbed);
}

// A post's body: its markdown, with each photo:// embed shown as the photo's
// thumbnail, scrapbook style, which opens it full size, from where you can
// page through the post's photos in order. photoUrls gives a URL to show
// instead, by key, for photos the CDN doesn't serve -- a draft's, until it's
// published.
function PostContent({ content, photoUrls = {} }) {
  const contentRef = useRef(null);
  const touchStartRef = useRef(null);
  // The full-size URLs of the post's embeds in order, and which is open.
  const [lightbox, setLightbox] = useState(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const lightboxSrc = lightbox && lightbox.srcs[lightbox.index];

  useEffect(() => {
    setImageLoaded(false);
    setImageError(false);
  }, [lightboxSrc]);

  const closeLightbox = useCallback(() => setLightbox(null), []);

  // Opens the embed clicked, among all of them as they read in the post.
  const openLightbox = useCallback((embed) => {
    const embeds = [...contentRef.current.querySelectorAll('.blog-photo-embed')];
    setLightbox({ srcs: embeds.map(el => el.dataset.fullsize), index: embeds.indexOf(embed) });
  }, []);

  const showPrev = useCallback(() => {
    setLightbox(lb => (lb && lb.index > 0) ? { ...lb, index: lb.index - 1 } : lb);
  }, []);

  const showNext = useCallback(() => {
    setLightbox(lb => (lb && lb.index < lb.srcs.length - 1) ? { ...lb, index: lb.index + 1 } : lb);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') closeLightbox();
      else if (e.key === 'ArrowLeft') showPrev();
      else if (e.key === 'ArrowRight') showNext();
    };
    if (lightbox) document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [lightbox, closeLightbox, showPrev, showNext]);

  const handleTouchStart = (e) => {
    const touch = e.touches[0];
    touchStartRef.current = { x: touch.clientX, y: touch.clientY };
  };

  const handleTouchEnd = (e) => {
    const start = touchStartRef.current;
    touchStartRef.current = null;
    if (!start) return;
    const touch = e.changedTouches[0];
    const dx = touch.clientX - start.x;
    const dy = touch.clientY - start.y;
    if (Math.abs(dx) > SWIPE_THRESHOLD && Math.abs(dx) > Math.abs(dy)) {
      if (dx < 0) showNext();
      else showPrev();
    }
  };

  const markdownComponents = {
    h1: ({ children }) => <h2>{children}</h2>,
    p: ({ node, children }) => (isPhotoRow(node)
      ? <div className="blog-photo-row">{children}</div>
      : <p>{children}</p>),
    code: ({ children, className }) => {
      const text = String(children).trim();
      if (!className && text.startsWith('photo://')) {
        const key = text.slice('photo://'.length);
        const s3Uri = `s3://${PHOTOS_BUCKET}/${key}`;
        const url = photoUrls[key];
        return (
          <PhotoEmbed
            photoKey={key}
            src={url || ApiService.getThumbnailUrl(s3Uri)}
            fullsize={url || ApiService.getFullsizeUrl(s3Uri)}
            onOpen={openLightbox}
          />
        );
      }
      return <code className={className}>{children}</code>;
    },
  };

  return (
    <>
      <div className="post-content" ref={contentRef}>
        <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>
      </div>

      {lightbox && (
        <div className="lightbox-overlay" onClick={closeLightbox}>
          {lightbox.index > 0 && (
            <button
              className="lightbox-nav lightbox-prev"
              onClick={e => { e.stopPropagation(); showPrev(); }}
              aria-label="Previous photo"
            >
              ‹
            </button>
          )}
          <div
            className="lightbox-content"
            onClick={e => e.stopPropagation()}
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
          >
            <button className="lightbox-close" onClick={closeLightbox}>✕</button>
            {!imageLoaded && !imageError && <div className="lightbox-loading">Loading...</div>}
            {imageError && <div className="lightbox-error">Failed to load image</div>}
            <img
              src={lightboxSrc}
              alt="Full size photo"
              className="lightbox-image"
              style={{ display: imageLoaded ? 'block' : 'none' }}
              onLoad={() => setImageLoaded(true)}
              onError={() => setImageError(true)}
            />
          </div>
          {lightbox.index < lightbox.srcs.length - 1 && (
            <button
              className="lightbox-nav lightbox-next"
              onClick={e => { e.stopPropagation(); showNext(); }}
              aria-label="Next photo"
            >
              ›
            </button>
          )}
        </div>
      )}
    </>
  );
}

export default PostContent;
