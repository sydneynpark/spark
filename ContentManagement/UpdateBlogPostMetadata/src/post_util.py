"""Reading blog posts: their metadata, from their S3 key and markdown.

This file is also, verbatim, ContentManagement/UpdateBlogPostMetadata/src/
post_util.py, which keeps the posts table (POSTS_TABLE) with it, so that the
table's items match what the admin page publishes and previews -- a test
there fails if the two differ. Edit this one, then copy it there.
"""
import re
from datetime import date as Date
import frontmatter

PHOTOS_BUCKET = 'spark.wiki.photos'
BLOG_BUCKET = 'spark.wiki.blog'
# Each post's metadata, its body aside, keyed by its s3_uri, with a
# slug-index to look posts up by slug.
POSTS_TABLE = 'spark.wiki.posts'
POSTS_SLUG_INDEX = 'slug-index'

# Posts embed photos as `photo://<key>`, either in inline code or as an
# image's URL (![alt](photo://<key>)), with <key> the photo's key in the
# photos bucket: birds/YYYY/MM/DD/<photo>.jpg for a bird photo, else
# photos/YYYY/MM/DD/<photo>.jpg. Keys can contain spaces, so a reference runs
# up to whatever closes it.
PHOTO_REF_PATTERN = re.compile(r'photo://([^`)\n]+)')
# Whole embeds, image or inline code, so previews can drop them.
EMBED_PATTERN = re.compile(r'!\[[^\]]*\]\([^)]*\)|`photo://[^`]*`')
DATE_PATH_PATTERN = re.compile(r'^\d{4}/\d{2}/\d{2}/')
DATE_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}')


def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def extract_preview(markdown_text, max_chars=160):
    """Return plain-text preview from markdown, skipping headings, photos
    and markup."""
    parts = []
    for line in markdown_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        line = EMBED_PATTERN.sub('', line)
        line = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
        line = re.sub(r'[*_`~]+', '', line)
        line = line.strip()
        if line:
            parts.append(line)
    text = ' '.join(parts)
    if len(text) > max_chars:
        return text[:max_chars].rstrip() + '...'
    return text


def photo_uri(ref):
    """The S3 URI of a photo given as `photo://<key>` or just <key>."""
    key = ref.strip()
    if key.startswith('photo://'):
        key = key[len('photo://'):]
    key = key.strip().lstrip('/')
    return f's3://{PHOTOS_BUCKET}/{key}' if key else None


def first_photo_uri(body):
    match = PHOTO_REF_PATTERN.search(body)
    return photo_uri(match.group(1)) if match else None


def _frontmatter_text(metadata, name):
    # As with book reviews, `or ''` covers both a missing key and one present
    # but empty (which YAML parses as None), and str(...) covers YAML parsing
    # an unquoted value as something other than a string (e.g. a number).
    return str(metadata.get(name, '') or '').strip()


def frontmatter_tags(value):
    """A post's tags, from its `tags` frontmatter: a YAML list, or a string
    of them separated by commas. Each is trimmed, with its whitespace
    collapsed, and the first spelling of one wins over any other in another
    case, as tags are matched regardless of case."""
    if value is None:
        return []
    items = value if isinstance(value, list) else str(value).split(',')
    tags = []
    seen = set()
    for item in items:
        tag = ' '.join(str(item if item is not None else '').replace(',', ' ').split())
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            tags.append(tag)
    return tags


def frontmatter_date(metadata, name='date'):
    """The date frontmatter gives as `name`, as 'YYYY-MM-DD', or None if it
    gives none that's a real date. YAML parses an unquoted 2026-05-23 as a
    date (and with a time, a datetime), and a quoted one as a string."""
    value = metadata.get(name)
    if isinstance(value, Date):
        return value.isoformat()[:10]
    text = str(value or '').strip()
    if not DATE_PATTERN.fullmatch(text):
        return None
    try:
        return Date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def parse_post(key, markdown_text):
    """A post's metadata and body, from its S3 key (YYYY/MM/DD/<name>.md)
    and markdown. Its date, title, slug, preview and photo can each be set
    in frontmatter; any that aren't fall back to being derived from the key
    or the body. The photo is None if neither has one, leaving the frontend to
    show a placeholder.

    A post has two dates: `date`, the one it's shown under -- for a post
    written later about something past, e.g. a trip, the trip's -- and
    `written`, when it was written, the same as `date` unless set. It has
    any number of tags, which the blog can be filtered by."""
    post = frontmatter.loads(markdown_text)
    metadata = post.metadata
    body = post.content

    date = frontmatter_date(metadata)
    if not date and DATE_PATH_PATTERN.match(key):
        year, month, day = key.split('/')[:3]
        date = f'{year}-{month}-{day}'
    name = key.split('/')[-1]
    if name.endswith('.md'):
        name = name[:-3]

    photo = _frontmatter_text(metadata, 'photo')
    return {
        'key': key,
        'date': date,
        'written': frontmatter_date(metadata, 'written') or date,
        'title': _frontmatter_text(metadata, 'title') or name.replace('-', ' ').replace('_', ' ').title(),
        'slug': slugify(_frontmatter_text(metadata, 'slug')) or slugify(name),
        'tags': frontmatter_tags(metadata.get('tags')),
        'preview': _frontmatter_text(metadata, 'preview') or extract_preview(body),
        'photo': photo_uri(photo) if photo else first_photo_uri(body),
        'content': body,
    }


def post_item(key, markdown_text, last_modified=None):
    """The posts table's item for the post at `key` in the blog bucket: what
    parse_post gives, but its body, and when the post was last modified (an
    ISO 8601 string), if given. Unset values are left out, rather than
    stored as nulls: the slug index can't have one."""
    post = parse_post(key, markdown_text)
    del post['content']
    item = {'s3_uri': f's3://{BLOG_BUCKET}/{key}', **post, 'last_modified': last_modified}
    return {name: value for name, value in item.items() if value is not None and value != ''}
