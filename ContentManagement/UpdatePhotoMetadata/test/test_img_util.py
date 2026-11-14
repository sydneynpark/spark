
import io
import unittest
from unittest.mock import MagicMock, patch
from PIL import Image
import test.sample_events as sample_events
import img_util


class TestImageUtil(unittest.TestCase):
    
    def setUp(self) -> None:
        self.img_util = img_util.ImageUtil()

    def test_get_exif(self):
        test_img = sample_events.TreeSwallowPhoto
        found_keywords = self.img_util.get_lightroom_keywords(test_img)

        for kword in ['Birds', 'Hirundinidae', 'PASSERIFORMES', 'Swallows- Martins', 'Tachycineta bicolor', 'Tree Swallow']:
            assert kword in found_keywords

    def test_get_date_captured(self):
        # A fresh stream, since TreeSwallowPhoto is a shared module-level
        # StreamingBody and test_get_exif already reads it to EOF.
        test_img = sample_events.file_to_streamingbody('tree-swallow')
        date_captured = self.img_util.get_date_captured(test_img)

        # DateTimeOriginal is 2025:05:17 09:51:56; the top-level DateTime tag
        # is 2025:05:20 (Lightroom's export date) and must not be used instead.
        assert date_captured == '2025-05-17'

    def test_create_thumbnail_turns_a_sideways_photo_upright(self):
        # Stored landscape, red in its top left corner, with an Orientation of
        # 6: turn 90 degrees clockwise to view, as a portrait.
        img = Image.new('RGB', (40, 30), 'blue')
        img.paste('red', (0, 0, 10, 10))
        exif = Image.Exif()
        exif[0x0112] = 6
        stored = io.BytesIO()
        img.save(stored, format='JPEG', exif=exif)
        stored.seek(0)

        with Image.open(self.img_util.create_thumbnail(stored, min_dimension=300)) as thumbnail:
            assert thumbnail.size == (300, 400)
            # The corner turned clockwise to the top right.
            r, g, b = thumbnail.getpixel((290, 10))
            assert r > 200 and b < 50

    def test_create_thumbnail_shrinks_a_large_photo_as_it_decodes(self):
        # 4000x3000, stored sideways, as a camera's portrait photo is.
        img = Image.new('RGB', (4000, 3000), 'blue')
        img.paste('red', (0, 0, 1000, 1000))
        exif = Image.Exif()
        exif[0x0112] = 6
        stored = io.BytesIO()
        img.save(stored, format='JPEG', exif=exif)
        stored.seek(0)

        resized_from = []
        resize = Image.Image.resize

        def spy(image, size, *args, **kwargs):
            resized_from.append(image.size)
            return resize(image, size, *args, **kwargs)

        with patch.object(Image.Image, 'resize', spy):
            thumbnail_stream = self.img_util.create_thumbnail(stored, min_dimension=300)

        # Decoded at 1/8 scale, and turned upright, rather than all 12 MP.
        assert resized_from == [(375, 500)]
        with Image.open(thumbnail_stream) as thumbnail:
            assert thumbnail.size == (300, 400)
            r, g, b = thumbnail.getpixel((290, 10))
            assert r > 200 and b < 50

if __name__ == '__main__':
    unittest.main()
