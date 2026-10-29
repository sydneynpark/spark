import re
import frontmatter

PHOTOS_BUCKET = 'spark.wiki.photos'

# Posts embed photos as `photo://<key>`, either in inline code or as an
# image's URL (![alt](photo://<key>)), with <key> the photo's key in the
# photos bucket: birds/YYYY/MM/DD/<photo>.jpg for a bird photo, else
# photos/YYYY/MM/DD/<photo>.jpg. Keys can contain spaces, so a reference runs
# up to whatever closes it.
PHOTO_REF_PATTERN = re.compile(r'photo://([^`)\n]+)')
# Whole embeds, image or inline code, so previews can drop them.
EMBED_PATTERN = re.compile(r'!\[[^\]]*\]\([^)]*\)|`photo://[^`]*`')
DATE_PATH_PATTERN = re.compile(r'^\d{4}/\d{2}/\d{2}/')


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


def parse_post(key, markdown_text):
    """A post's metadata and body, from its S3 key (YYYY/MM/DD/<name>.md)
    and markdown. Its title, slug, preview and photo can each be set in
    frontmatter; any that aren't fall back to being derived from the key or
    the body. The photo is None if neither has one, leaving the frontend to
    show a placeholder."""
    post = frontmatter.loads(markdown_text)
    metadata = post.metadata
    body = post.content

    date = None
    if DATE_PATH_PATTERN.match(key):
        year, month, day = key.split('/')[:3]
        date = f'{year}-{month}-{day}'
    name = key.split('/')[-1]
    if name.endswith('.md'):
        name = name[:-3]

    photo = _frontmatter_text(metadata, 'photo')
    return {
        'key': key,
        'date': date,
        'title': _frontmatter_text(metadata, 'title') or name.replace('-', ' ').replace('_', ' ').title(),
        'slug': slugify(_frontmatter_text(metadata, 'slug')) or slugify(name),
        'preview': _frontmatter_text(metadata, 'preview') or extract_preview(body),
        'photo': photo_uri(photo) if photo else first_photo_uri(body),
        'content': body,
    }
