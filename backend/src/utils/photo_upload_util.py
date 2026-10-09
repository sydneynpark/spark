"""Path rules for admin photo uploads into spark.wiki.photos.

The bucket is laid out as YYYY/MM/DD/<filename>, and UpdatePhotoMetadata
falls back to that path for a photo's date when it has no EXIF capture date,
so new folders can only extend that structure (a year, then a month, then a
day) and photos can only be uploaded into a day folder.
"""
import os
import re
from datetime import date

DATE_LEVELS = ('year', 'month', 'day')
_DATE_SEGMENT_PATTERNS = (r'\d{4}', r'\d{2}', r'\d{2}')
_FOLDER_NAME_HINTS = (
    'A year folder is 4 digits, like 2026.',
    'A month folder is 1-12.',
    "A day folder is a day in that folder's month, like 7 or 23.",
)

PHOTO_CONTENT_TYPE = 'image/jpeg'
# The rest of the pipeline (Lightroom keyword parsing, thumbnails) is built
# around JPEG exports.
PHOTO_EXTENSIONS = ('.jpg', '.jpeg')


class UploadPathError(ValueError):
    """A folder or filename the admin asked for that breaks the layout
    above -- its message is shown to them as-is."""


def validate_prefix(prefix):
    """Return an error message if `prefix` isn't a folder path that's safe
    to list ('' for the bucket root, else segments each ending in '/'), or
    None if it is. Folders outside the date structure (like archive/) can
    still be browsed."""
    if prefix == '':
        return None
    segments = prefix.split('/')
    if not prefix.endswith('/') or '\\' in prefix or any(s in ('', '.', '..') for s in segments[:-1]):
        return f'Invalid folder path: {prefix!r}'
    return None


def _date_depth(prefix):
    """How far down YYYY/MM/DD/ `prefix` is: 0 at the bucket root, 1 in a
    year folder, 2 in a month, 3 in a day -- or None if it isn't on that
    path (including dates that don't exist, like 2025/02/30/)."""
    if prefix and not prefix.endswith('/'):
        return None
    segments = prefix.split('/')[:-1]
    if len(segments) > 3:
        return None
    if not all(re.fullmatch(pattern, s) for pattern, s in zip(_DATE_SEGMENT_PATTERNS, segments)):
        return None
    if not segments:
        return 0
    year, month, day = (segments + ['01', '01'])[:3]
    try:
        date(int(year), int(month), int(day))
    except ValueError:
        return None
    return len(segments)


def child_folder_kind(prefix):
    """'year', 'month', or 'day': the kind of folder that can be created
    inside `prefix`, or None if none can."""
    depth = _date_depth(prefix)
    return DATE_LEVELS[depth] if depth is not None and depth < len(DATE_LEVELS) else None


def accepts_uploads(prefix):
    return _date_depth(prefix) == len(DATE_LEVELS)


def new_folder_prefix(parent, name):
    """The prefix for a new `name` folder inside `parent`, zero-padding
    single-digit months and days. Raises UploadPathError if it wouldn't be
    the next level of the date structure."""
    kind = child_folder_kind(parent)
    if kind is None:
        raise UploadPathError('New folders can only be a year, month, or day, inside YYYY/MM/DD/.')

    name = (name or '').strip()
    padded = f'0{name}' if kind != 'year' and re.fullmatch(r'\d', name) else name

    prefix = f'{parent}{padded}/'
    depth = DATE_LEVELS.index(kind)
    if _date_depth(prefix) != depth + 1:
        raise UploadPathError(f'"{name}" isn\'t a valid {kind} folder. {_FOLDER_NAME_HINTS[depth]}')
    return prefix


def photo_key(folder, filename):
    """The S3 key a photo named `filename` is uploaded to in `folder`.
    Raises UploadPathError if `folder` isn't a day folder or `filename`
    isn't a plain JPEG filename."""
    if not accepts_uploads(folder):
        raise UploadPathError('Photos can only be uploaded into a day folder (YYYY/MM/DD/).')

    filename = filename or ''
    if (not filename.strip() or filename.startswith('.') or len(filename) > 255
            or any(c in filename for c in '/\\') or any(ord(c) < 32 for c in filename)):
        raise UploadPathError(f'Invalid filename: {filename!r}')
    if os.path.splitext(filename)[1].lower() not in PHOTO_EXTENSIONS:
        raise UploadPathError(f'"{filename}" isn\'t a JPEG -- only .jpg/.jpeg photos are supported.')
    return f'{folder}{filename}'
