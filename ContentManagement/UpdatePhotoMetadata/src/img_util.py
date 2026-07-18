from PIL import Image, ExifTags
from datetime import datetime
import io

EXIF_DATE_FORMAT = '%Y:%m:%d %H:%M:%S'

class ImageUtil:

    def __init__(self):
        pass

    def get_lightroom_keywords(self, jpg_stream):
        with Image.open(jpg_stream) as img:
            img_xmp = img.getxmp()
            keyword_list = img_xmp['xmpmeta']['RDF']['Description']['subject']['Bag']['li']
            return keyword_list

    def get_date_captured(self, jpg_stream):
        # DateTimeOriginal is the capture date; the top-level DateTime tag is the
        # file's last-modified/export date instead, so it's never used as a fallback.
        with Image.open(jpg_stream) as img:
            exif_ifd = img.getexif().get_ifd(ExifTags.IFD.Exif)
            for tag in (ExifTags.Base.DateTimeOriginal, ExifTags.Base.DateTimeDigitized):
                raw = exif_ifd.get(tag)
                if raw:
                    try:
                        return datetime.strptime(raw, EXIF_DATE_FORMAT).strftime('%Y-%m-%d')
                    except (ValueError, TypeError):
                        pass
        return None

    def create_thumbnail(self, jpg_stream, min_dimension=300):
        with Image.open(jpg_stream) as img:
            w, h = img.size
            if w <= h:
                new_w = min_dimension
                new_h = round(h * min_dimension / w)
            else:
                new_h = min_dimension
                new_w = round(w * min_dimension / h)
            thumbnail = img.resize((new_w, new_h), Image.LANCZOS)
            buf = io.BytesIO()
            thumbnail.save(buf, format='JPEG')
            buf.seek(0)
            return buf
