"""Blog post drafts, which the admin page writes, previews, and publishes.

A draft is kept in the blog bucket under drafts/<id>/, apart from the posts'
YYYY/MM/DD/ layout, and ContentAPI can't read it (terraform/site_api.tf):

* drafts/<id>/draft.md: its markdown, in the same format as a post's.
* drafts/<id>/<collection>/<filename>: the photos uploaded to it, 'birds' or
  'photos' as they'll be published. A post embeds one as
  photo://drafts/<id>/<collection>/<filename>.

The photos wait there, rather than in the photos bucket, so that
UpdatePhotoMetadata doesn't put them on the site before the post is. When it
is, they're copied into their collection's folder for the post's date, the
post's embeds of them are pointed there, and the draft is deleted.
"""
import re
import uuid

import frontmatter
import yaml

from utils.photo_upload_util import PHOTO_COLLECTIONS, photo_key, validate_photo_filename
from utils.post_util import PHOTO_REF_PATTERN, frontmatter_date, slugify

DRAFTS_PREFIX = 'drafts/'
DRAFT_FILENAME = 'draft.md'
DRAFT_ID_PATTERN = re.compile(r'[0-9a-f]{32}')
# In the order they're written to a post's frontmatter.
FRONTMATTER_FIELDS = ('title', 'date', 'written', 'preview', 'photo')
MAX_TITLE_LENGTH = 200
MAX_PREVIEW_LENGTH = 500


class DraftError(ValueError):
    """Something about a draft that stops it being saved or published --
    its message is shown to the admin as-is."""


def new_draft_id():
    return uuid.uuid4().hex


def is_draft_id(value):
    return bool(DRAFT_ID_PATTERN.fullmatch(value or ''))


def draft_prefix(draft_id):
    return f'{DRAFTS_PREFIX}{draft_id}/'


def draft_key(draft_id):
    return f'{draft_prefix(draft_id)}{DRAFT_FILENAME}'


def draft_id_from_key(key):
    """The ID of the draft whose markdown is at `key`, or None if it isn't
    one's."""
    match = re.fullmatch(rf'{DRAFTS_PREFIX}({DRAFT_ID_PATTERN.pattern})/{DRAFT_FILENAME}', key)
    return match.group(1) if match else None


def draft_photo_key(draft_id, collection, filename):
    """Where a photo named `filename`, for `collection`, is uploaded to in
    the draft. Raises UploadPathError if it isn't a plain JPEG filename."""
    validate_photo_filename(filename)
    return f'{draft_prefix(draft_id)}{collection}/{filename}'


def draft_photo(draft_id, key):
    """A photo uploaded to the draft, from its key, as the admin page lists
    it: its collection, filename, and how a post embeds it. None if `key`
    isn't one."""
    rest = key[len(draft_prefix(draft_id)):] if key.startswith(draft_prefix(draft_id)) else ''
    collection, _, filename = rest.partition('/')
    if not filename or '/' in filename:
        return None
    return {'key': key, 'collection': collection, 'filename': filename, 'ref': f'photo://{key}'}


def draft_fields(payload):
    """The draft fields in a request's JSON, as strings, checking what can be
    checked before it's published. A draft can be saved with no title or
    date yet, but not with a date that isn't one. Its `written` date is
    optional even to publish: without one, it's the same as its `date`."""
    fields = {name: str(payload.get(name) or '').strip() for name in FRONTMATTER_FIELDS}
    fields['content'] = str(payload.get('content') or '')

    if len(fields['title']) > MAX_TITLE_LENGTH:
        raise DraftError(f'The title is longer than {MAX_TITLE_LENGTH} characters.')
    if len(fields['preview']) > MAX_PREVIEW_LENGTH:
        raise DraftError(f'The preview text is longer than {MAX_PREVIEW_LENGTH} characters.')
    for name in ('date', 'written'):
        if fields[name] and frontmatter_date(fields, name) is None:
            raise DraftError(f'"{fields[name]}" isn\'t a date (YYYY-MM-DD).')
    if fields['photo'] and not fields['photo'].startswith('photo://'):
        raise DraftError('The thumbnail photo should be a photo://<key> reference.')
    return fields


def build_markdown(fields):
    """A draft's or post's file content: its frontmatter (just the fields it
    has), then its body."""
    metadata = {name: fields[name] for name in FRONTMATTER_FIELDS if fields.get(name)}
    body = fields.get('content', '')
    if not metadata:
        return body
    front_matter = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
    return f'---\n{front_matter}---\n\n{body}'


def parse_draft(markdown_text):
    """A draft's fields, as the editor edits them -- unlike parse_post,
    with nothing filled in for what it hasn't set yet."""
    post = frontmatter.loads(markdown_text)
    fields = {name: str(post.metadata.get(name) or '').strip() for name in FRONTMATTER_FIELDS}
    fields['date'] = frontmatter_date(post.metadata) or ''
    fields['written'] = frontmatter_date(post.metadata, 'written') or ''
    fields['content'] = post.content
    return fields


def plan_publish(draft_id, fields, photo_keys):
    """What publishing the draft writes, given its fields and the keys of the
    photos uploaded to it: the post's key in the blog bucket
    (YYYY/MM/DD/<slug>.md), the post's markdown, its slug, and each photo's
    key in the photos bucket (<collection>/YYYY/MM/DD/<filename>, by the
    post's date), keyed by its key in the draft. Raises DraftError if the
    draft isn't ready to publish.

    Every photo uploaded to the draft is published, whether the post embeds
    it or not, so a photo can go up along with a post without being in it.
    """
    title = fields.get('title', '')
    if not title:
        raise DraftError('Give the post a title before publishing it.')
    slug = slugify(title)
    if not slug:
        raise DraftError('The title needs at least one letter or number, for the post\'s URL.')
    # Already checked to be a real date, if there is one, by draft_fields.
    date = fields.get('date', '')
    if not date:
        raise DraftError('Give the post a date before publishing it.')

    folder = f'{date.replace("-", "/")}/'
    photos = {}
    for key in photo_keys:
        photo = draft_photo(draft_id, key)
        if not photo or photo['collection'] not in PHOTO_COLLECTIONS:
            raise DraftError(f'"{key}" isn\'t a photo this draft can publish.')
        photos[key] = PHOTO_COLLECTIONS[photo['collection']] + photo_key(folder, photo['filename'])

    def published_ref(match):
        key = match.group(1).strip()
        if not key.startswith(DRAFTS_PREFIX):
            return match.group(0)
        if key not in photos:
            raise DraftError(f'The post embeds {key.split("/")[-1]}, which isn\'t uploaded to this draft anymore.')
        return match.group(0).replace(key, photos[key])

    published = {
        **fields,
        'content': PHOTO_REF_PATTERN.sub(published_ref, fields.get('content', '')),
        'photo': PHOTO_REF_PATTERN.sub(published_ref, fields.get('photo', '')),
    }
    return {
        'key': f'{folder}{slug}.md',
        'slug': slug,
        'markdown': build_markdown(published),
        'photos': photos,
    }
