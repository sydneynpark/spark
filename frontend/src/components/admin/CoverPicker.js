import { useState } from 'react';
import ApiService from '../../services/api';
import { shrinkCoverToJpeg } from '../../utils/coverImage';

// A book's custom covers live under covers/custom/ in the books bucket; any
// other cover was looked up on Google Books.
function isCustomCover(coverKey) {
  return Boolean(coverKey) && coverKey.startsWith('covers/custom/');
}

// The book review form's cover: the one it has, and a way to replace it
// with an image of your own, or go back to Google Books' one.
//
// - coverImage: the custom cover saved in the review (its S3 key), or null.
// - liveCoverKey: the cover the site shows for the book now (editing only).
// - newCover: { blob, url } for an image chosen but not yet uploaded -- the
//   form uploads it when it's saved.
function CoverPicker({ isEditing, coverImage, liveCoverKey, newCover, onNewCover, onUseLookedUpCover }) {
  const [error, setError] = useState(null);

  async function handleFile(e) {
    const file = e.target.files[0];
    // So choosing the same file again still fires a change.
    e.target.value = '';
    if (!file) return;
    setError(null);
    try {
      const blob = await shrinkCoverToJpeg(file);
      onNewCover({ blob, url: URL.createObjectURL(blob) });
    } catch (err) {
      setError(err.message);
    }
  }

  let src = null;
  let caption;
  let action = null;
  if (newCover) {
    src = newCover.url;
    caption = `New cover, uploaded when you ${isEditing ? 'save' : 'submit'}.`;
    action = <button type="button" className="admin-remove-button" onClick={() => onNewCover(null)}>Discard</button>;
  } else if (coverImage) {
    src = ApiService.getBookCoverUrl(coverImage);
    caption = 'Custom cover.';
    action = (
      <button type="button" className="admin-remove-button" onClick={onUseLookedUpCover}>
        Use Google Books' cover instead
      </button>
    );
  } else if (isEditing && liveCoverKey && !isCustomCover(liveCoverKey)) {
    src = ApiService.getBookCoverUrl(liveCoverKey);
    caption = 'From Google Books.';
  } else if (isEditing && isCustomCover(liveCoverKey)) {
    caption = "Google Books' cover, looked up when the review is saved.";
  } else if (isEditing) {
    caption = 'Google Books had no cover for this book.';
  } else {
    caption = 'Looked up on Google Books when you submit, unless you upload one.';
  }

  return (
    <section className="admin-form-section">
      <h3>Cover</h3>
      <div className="admin-cover-picker">
        <img
          className="admin-cover-preview"
          src={src || '/images/placeholder-book.jpg'}
          alt=""
          onError={e => { e.target.src = '/images/placeholder-book.jpg'; }}
        />
        <div className="admin-cover-details">
          <p className="admin-form-hint">{caption}</p>
          {error && <p className="error">{error}</p>}
          <div className="admin-cover-actions">
            <label className="admin-add-button admin-cover-upload">
              {src ? 'Upload a different cover' : 'Upload a cover'}
              <input type="file" accept="image/*" onChange={handleFile} />
            </label>
            {action}
          </div>
        </div>
      </div>
    </section>
  );
}

export default CoverPicker;
