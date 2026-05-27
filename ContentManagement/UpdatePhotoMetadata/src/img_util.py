from PIL import Image, ExifTags
import io

class ImageUtil:

    def __init__(self):
        pass

    def get_lightroom_keywords(self, jpg_stream):
        with Image.open(jpg_stream) as img:
            img_xmp = img.getxmp()
            keyword_list = img_xmp['xmpmeta']['RDF']['Description']['subject']['Bag']['li']
            return keyword_list

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
