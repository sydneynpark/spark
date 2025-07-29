from PIL import Image, ExifTags

class ImageUtil:

    def __init__(self):
        pass

    def get_lightroom_keywords(self, jpg_stream):
        with Image.open(jpg_stream) as img:
            img_xmp = img.getxmp()
            keyword_list = img_xmp['xmpmeta']['RDF']['Description']['subject']['Bag']['li']
            return keyword_list
