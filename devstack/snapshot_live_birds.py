"""
Copies a selection of the bird photos live on spark.wiki into
sample-data/photos/originals/birds, for the local stack to start with (see
sample-data/README.md). Run it with ./dev snapshot-birds.

The full-size photos are shrunk, to keep the repository small, but keep the
metadata UpdatePhotoMetadata reads -- Lightroom's keywords (XMP) and the
capture date (EXIF) -- and each is checked to still give the species and
date the live site has for it.
"""

import io
import json
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
LAMBDA_SRC = REPO / 'ContentManagement' / 'UpdatePhotoMetadata' / 'src'
sys.path.insert(0, str(LAMBDA_SRC))

import img_util  # noqa: E402
import lambda_function  # noqa: E402
import taxonomy_util  # noqa: E402

API_URL = 'https://api.spark.wiki'
PHOTOS_CDN_URL = 'https://photos.spark.wiki'

ORIGINALS_DIR = REPO / 'sample-data' / 'photos' / 'originals' / 'birds'

# Enough of the site's dates and taxonomy to fill out both of the photos
# page's trees: families with more than one species, a species with photos
# from more than one day, and a photo of more than one species.
SELECTED = [
    '2026/02/27/2026-02-27 - 864A3887.jpg',  # Mallard
    '2026/02/27/2026-02-27 - 864A3942.jpg',  # Wood Duck
    '2026/03/15/2026-03-15 - 864A5374.jpg',  # Acorn Woodpecker
    '2026/03/22/2026-03-22 - 864A5958.jpg',  # California Scrub Jay
    '2026/03/22/2026-03-22 - 864A6054.jpg',  # American Kestrel
    '2026/03/22/2026-03-22 - 864A6423.jpg',  # California Quail
    '2026/04/25/2026-04-25 - 864A7298.jpg',  # Peregrine Falcon
    '2026/05/23/2026-05-23 - 864A7759.jpg',  # Pied-billed Grebe
    '2026/05/23/2026-05-23 - 864A8210.jpg',  # Snowy Egret
    '2026/05/23/2026-05-23 - 864A8618-2.jpg',  # Common Yellowthroat
    '2026/05/29/2026-05-29 - 864A8849.jpg',  # Bewick's Wren
    '2026/05/30/2026-05-30 - 864A9054-2.jpg',  # Cassin's Kingbird + Red-tailed Hawk
    '2026/06/22/2026-06-22 - Red-tailed Hawk 02.jpg',
    '2026/06/22/2026-06-22 - Red-tailed Hawk 05.jpg',
    "2026/08/06/2026-08-06 - Allen's Hummingbird 06.jpg",
    '2026/08/06/2026-08-06 - American Bushtit 15.jpg',
    "2026/08/06/2026-08-06 - Anna's Hummingbird 05.jpg",
    '2026/08/09/2026-08-09 - Western Gull 03.jpg',
    '2026/08/09/2026-08-09 - Yellow-crowned Night Heron 09.jpg',
]

# Plenty for the site's full-size view.
MAX_DIMENSION = 2048
JPEG_QUALITY = 82

# EXIF's GPS block: where the photo was taken, which nothing reads.
GPS_IFD = 0x8825

# Where the bird photos are; SELECTED's keys are within it.
BIRDS_URI = 's3://spark.wiki.photos/birds/'

images = img_util.ImageUtil()
taxonomy = taxonomy_util.TaxonomyUtil(str(LAMBDA_SRC / 'Bird keywords.txt'))


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'spark.wiki devstack snapshot'})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def live_species_and_dates():
    """Each live photo's species, and date, by key, as the site has them."""
    photos = json.loads(fetch(f'{API_URL}/birds'))['photos']
    live = {}
    for photo in photos:
        key = photo['s3_uri'][len(BIRDS_URI):]
        species, date = live.get(key, (set(), photo.get('date')))
        live[key] = (species | {photo['species']}, date)
    return live


def compress(original):
    with Image.open(io.BytesIO(original)) as img:
        exif = img.getexif()
        exif.pop(GPS_IFD, None)
        xmp = img.info.get('xmp')
        icc_profile = img.info.get('icc_profile')

        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
        out = io.BytesIO()
        img.save(
            out,
            format='JPEG',
            quality=JPEG_QUALITY,
            optimize=True,
            progressive=True,
            exif=exif,
            xmp=xmp,
            icc_profile=icc_profile,
        )
        return out.getvalue()


def species_and_date(key, photo):
    """What UpdatePhotoMetadata reads from the photo."""
    keywords = images.get_lightroom_keywords(io.BytesIO(photo))
    species = {t['species'] for t in taxonomy.parse_keywords_to_taxonomy(keywords)}
    date = images.get_date_captured(io.BytesIO(photo)) or lambda_function._date_from_key(key)
    return species, date


def main():
    live = live_species_and_dates()
    missing = [key for key in SELECTED if key not in live]
    if missing:
        sys.exit(f'Not live (any more): {", ".join(missing)}')

    # Made afresh, so photos that are no longer selected go too.
    shutil.rmtree(ORIGINALS_DIR, ignore_errors=True)

    total = 0
    for key in SELECTED:
        path = '/'.join(urllib.parse.quote(part) for part in key.split('/'))
        original = fetch(f'{PHOTOS_CDN_URL}/birds/{path}')
        photo = compress(original)

        found = species_and_date(key, photo)
        if found != live[key]:
            sys.exit(f'{key} reads as {found} once compressed, rather than {live[key]} as on the site')

        out_path = ORIGINALS_DIR / key
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(photo)
        total += len(photo)
        print(f'{key}: {len(original) / 1e6:.1f} MB -> {len(photo) / 1e3:.0f} KB ({", ".join(sorted(found[0]))})')

    print(f'Wrote {len(SELECTED)} photo(s), {total / 1e6:.1f} MB in all, to {ORIGINALS_DIR.relative_to(REPO)}')


if __name__ == '__main__':
    main()
